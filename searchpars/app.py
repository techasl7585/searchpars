from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from .actions import ACTIONS, run_action
from .ai import OllamaProvider
from .indexer import SearchIndex
from .models import SearchIntent, SearchResult
from .nlp import normalize, parse_local
from .router import route_query
from .websearch import WebSearchProvider


def open_target(result: SearchResult) -> None:
    if result.result_type == "application":
        if shutil.which("gtk-launch"):
            subprocess.Popen(["gtk-launch", Path(result.target).stem])
        elif shutil.which("gio"):
            subprocess.Popen(["gio", "launch", result.target])
        else:
            raise OSError("GTK/GIO uygulama başlatıcısı bulunamadı")
    else:
        subprocess.Popen(["xdg-open", result.target])


def cli(query: str, rebuild: bool = False) -> int:
    index = SearchIndex()
    if rebuild or index.stats().files == 0:
        stats = index.rebuild()
        print(f"{stats.files} dosya, {stats.applications} uygulama indekslendi.")
    provider = OllamaProvider()
    intent = parse_local(query)
    decision = route_query(query, intent)
    if intent.intent == "action" and intent.action:
        success, message = run_action(intent.action)
        print(message)
        return 0 if success else 1
    local_results = index.search(intent) if decision.use_local else []
    web_results = WebSearchProvider().search(query) if decision.use_web else []
    if provider.available() and decision.use_ai:
        answer = provider.answer_with_sources(query, local_results, web_results)
        if answer:
            print(f"YAPAY ZEKÂ\n{answer}\n")
    for result in local_results + web_results:
        print(f"{result.result_type:11} {result.title}\n            {result.subtitle}")
    return 0


def gui() -> int:
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, GLib, Gtk
    except (ImportError, ValueError):
        print(
            "GTK bulunamadı. Kurulum için: sudo apt install python3-gi gir1.2-gtk-3.0",
            file=sys.stderr,
        )
        return 1

    class SearchParsWindow(Gtk.Window):
        def __init__(self) -> None:
            super().__init__(title="SearchPars")
            self.set_default_size(1180, 700)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_icon_name("searchpars")
            self.index = SearchIndex()
            self.provider = OllamaProvider()
            self.web = WebSearchProvider()
            self.current_results: list[SearchResult] = []
            self.local_results: list[SearchResult] = []
            self.web_results: list[SearchResult] = []
            self.search_generation = 0
            self.timeout_id: int | None = None
            self._build_ui()
            self._load_css()
            self.connect("destroy", Gtk.main_quit)
            self.connect("key-press-event", self._on_key)
            GLib.idle_add(self._startup)

        def _build_ui(self) -> None:
            root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            root.get_style_context().add_class("app-root")
            self.add(root)

            top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            top.set_border_width(18)
            top.get_style_context().add_class("search-area")
            root.pack_start(top, False, False, 0)

            logo = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.DIALOG)
            logo.get_style_context().add_class("search-logo")
            top.pack_start(logo, False, False, 0)

            self.entry = Gtk.SearchEntry()
            self.entry.set_placeholder_text(
                "Dosya, uygulama, web, soru veya Pardus komutu yaz…"
            )
            self.entry.set_hexpand(True)
            self.entry.connect("search-changed", self._on_search_changed)
            self.entry.connect("activate", self._activate_selected)
            top.pack_start(self.entry, True, True, 0)

            refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
            refresh.set_tooltip_text("Arama dizinini yenile")
            refresh.connect("clicked", lambda _button: self._rebuild())
            top.pack_start(refresh, False, False, 0)

            self.ai_badge = Gtk.Label(label="Yapay zekâ kontrol ediliyor…")
            self.ai_badge.set_xalign(0)
            self.ai_badge.get_style_context().add_class("ai-badge")
            root.pack_start(self.ai_badge, False, False, 12)

            content = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            content.set_position(740)
            root.pack_start(content, True, True, 0)

            scroller = Gtk.ScrolledWindow()
            scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            self.listbox = Gtk.ListBox()
            self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
            self.listbox.connect("row-activated", self._row_activated)
            self.listbox.connect("row-selected", self._row_selected)
            scroller.add(self.listbox)
            content.pack1(scroller, resize=True, shrink=False)

            detail_scroller = Gtk.ScrolledWindow()
            detail_scroller.set_policy(
                Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC
            )
            detail_scroller.set_size_request(360, -1)
            self.detail_panel = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL, spacing=12
            )
            self.detail_panel.set_border_width(20)
            self.detail_panel.get_style_context().add_class("detail-panel")
            self.detail_title = Gtk.Label(label="Yapay Zekâ Ayrıntısı")
            self.detail_title.set_xalign(0)
            self.detail_title.set_line_wrap(True)
            self.detail_title.get_style_context().add_class("detail-title")
            self.detail_panel.pack_start(self.detail_title, False, False, 0)
            self.detail_label = Gtk.Label(
                label=(
                    "Bir soru sor veya soldaki sonucu seç. Ayrıntılı cevap ve "
                    "kaynaklar burada gösterilecek."
                )
            )
            self.detail_label.set_xalign(0)
            self.detail_label.set_yalign(0)
            self.detail_label.set_line_wrap(True)
            self.detail_label.set_selectable(True)
            self.detail_label.set_max_width_chars(48)
            self.detail_panel.pack_start(self.detail_label, False, False, 0)
            self.detail_source = Gtk.Label(label="")
            self.detail_source.set_xalign(0)
            self.detail_source.set_yalign(0)
            self.detail_source.set_line_wrap(True)
            self.detail_source.set_selectable(True)
            self.detail_source.get_style_context().add_class("detail-source")
            self.detail_panel.pack_start(self.detail_source, False, False, 0)
            detail_scroller.add(self.detail_panel)
            content.pack2(detail_scroller, resize=False, shrink=False)

            self.empty = Gtk.Label(label="Aramak istediğin şeyi doğal dille yaz.")
            self.empty.set_margin_top(90)
            self.empty.get_style_context().add_class("empty-label")
            self.listbox.set_placeholder(self.empty)

            footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            footer.set_border_width(12)
            footer.get_style_context().add_class("footer")
            self.status = Gtk.Label(label="")
            self.status.set_xalign(0)
            footer.pack_start(self.status, True, True, 0)
            hint = Gtk.Label(label="↑↓ seç  •  Enter aç  •  Esc kapat")
            footer.pack_end(hint, False, False, 0)
            root.pack_end(footer, False, False, 0)

        def _load_css(self) -> None:
            css = b"""
            window, .app-root { background: #10131a; color: #f5f7ff; }
            .search-area { background: #191e29; border-radius: 18px; }
            searchentry {
              min-height: 48px; font-size: 18px; border: none;
              background: transparent; color: #ffffff;
            }
            .search-logo { color: #78a9ff; }
            .ai-badge {
              color: #a9c7ff; background: #172748; border-radius: 10px;
              padding: 6px 12px; margin-left: 16px; margin-right: 16px;
            }
            .detail-panel {
              background: #151b27; border-left: 1px solid #2b3445;
            }
            .detail-title { color: #ffffff; font-size: 18px; font-weight: 700; }
            .detail-source { color: #8faee6; font-size: 11px; }
            list { background: transparent; }
            list row {
              padding: 12px 16px; margin: 3px 12px; border-radius: 12px;
            }
            list row:selected { background: #244f91; }
            .result-title { font-size: 15px; font-weight: 600; color: #ffffff; }
            .result-subtitle { color: #aeb7c8; font-size: 12px; }
            .result-snippet { color: #d1d8e5; font-size: 12px; }
            .section-title {
              color: #78a9ff; font-size: 12px; font-weight: 700;
              padding-top: 5px; padding-bottom: 2px;
            }
            .empty-label { color: #768195; font-size: 15px; }
            .footer { background: #141822; color: #8f9aaf; }
            """
            provider = Gtk.CssProvider()
            provider.load_from_data(css)
            screen = Gdk.Screen.get_default()
            Gtk.StyleContext.add_provider_for_screen(
                screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        def _startup(self) -> bool:
            available = self.provider.available()
            if available:
                self.ai_badge.set_text(
                    f"● Yerel yapay zekâ etkin — {self.provider.model}"
                )
            else:
                self.ai_badge.set_text(
                    "○ Hızlı yerel yorumlama — yapay zekâ modeli kurulmamış"
                )
            self._rebuild()
            self.entry.grab_focus()
            return False

        def _rebuild(self) -> None:
            self.status.set_text("Dosyalar indeksleniyor…")
            self.ai_badge.set_sensitive(False)
            self.entry.set_sensitive(False)

            def work() -> None:
                stats = self.index.rebuild(
                    progress=lambda message: GLib.idle_add(self.status.set_text, message)
                )
                GLib.idle_add(self._rebuild_done, stats)

            threading.Thread(target=work, daemon=True).start()

        def _rebuild_done(self, stats) -> bool:
            self.ai_badge.set_sensitive(True)
            self.entry.set_sensitive(True)
            self.entry.grab_focus()
            self.status.set_text(
                f"{stats.files} dosya ve {stats.applications} uygulama indekslendi"
            )
            if self.entry.get_text().strip():
                self._queue_search()
            return False

        def _on_search_changed(self, _entry) -> None:
            if self.timeout_id:
                GLib.source_remove(self.timeout_id)
            self.timeout_id = GLib.timeout_add(220, self._queue_search)

        def _queue_search(self) -> bool:
            self.timeout_id = None
            query = self.entry.get_text().strip()
            self.search_generation += 1
            generation = self.search_generation
            self.detail_title.set_text("Arama hazırlanıyor")
            self.detail_label.set_text("Yerel ve çevrim içi kaynaklar kontrol ediliyor…")
            self.detail_source.set_text("")
            self.local_results = []
            self.web_results = []
            if not query:
                self._show_results([])
                self.empty.set_text("Aramak istediğin şeyi doğal dille yaz.")
                return False

            intent = parse_local(query)
            decision = route_query(query, intent)
            if intent.intent == "action" and intent.action in ACTIONS:
                action = ACTIONS[intent.action]
                self.local_results = [
                    SearchResult(
                        result_type="action",
                        title=action.title,
                        subtitle=action.description,
                        target=intent.action,
                        score=100,
                        icon=action.icon,
                    )
                ]
                self._render_sections()
                self.status.set_text(
                    f"İşlemi anladım: {action.title}. Enter ile çalıştır."
                )
                return False

            if decision.use_local:
                self.local_results = self.index.search(intent)
            self._render_sections()

            if decision.route == "application":
                app_result = self._exact_application(query)
                if app_result:
                    self.status.set_text(f"{app_result.title} açılıyor…")
                    GLib.timeout_add(
                        250, self._launch_application, app_result, generation
                    )
                    return False

            if decision.use_web:
                self.status.set_text(
                    f"{len(self.local_results)} yerel sonuç bulundu; web aranıyor…"
                )
                self.ai_badge.set_text("● Web ve kaynaklar aranıyor…")

                def web_work() -> None:
                    results = self.web.search(query)
                    GLib.idle_add(self._web_search_done, query, results, generation)

                threading.Thread(target=web_work, daemon=True).start()
            else:
                self._finish_local_search(query, intent, generation)
            return False

        def _exact_application(self, query: str) -> SearchResult | None:
            command = normalize(query)
            command = re.sub(r"\b(aç|çalıştır|başlat)\b", " ", command)
            command = " ".join(command.split())
            if not command:
                return None
            applications = [
                result
                for result in self.local_results
                if result.result_type == "application"
            ]
            for result in applications:
                app_name = normalize(result.title)
                if app_name == command or app_name in command or command in app_name:
                    return result
            return None

        def _launch_application(
            self, result: SearchResult, generation: int
        ) -> bool:
            if generation != self.search_generation:
                return False
            try:
                open_target(result)
                self.close()
            except OSError as exc:
                self.status.set_text(f"Uygulama açılamadı: {exc}")
            return False

        def _finish_local_search(
            self, query: str, intent: SearchIntent, generation: int
        ) -> None:
            self.ai_badge.set_text("● Yerel dosya araması tamamlandı")
            count = len(self.local_results)
            if count:
                message = (
                    f"Bilgisayarında {count} uygun sonuç buldum. "
                    f"En iyi eşleşme: {self.local_results[0].title}"
                )
            else:
                message = "Bilgisayarında bu isteğe uyan sonuç bulamadım."
                self.empty.set_text("Yerel sonuç bulunamadı.")
            self.status.set_text(message)
            self._show_answer(message, generation)

            if self.provider.available() and intent.answer_needed and self.local_results:
                self.ai_badge.set_text(
                    f"● Dosyalara göre cevap hazırlanıyor — {self.provider.model}"
                )

                def answer_work() -> None:
                    answer = self.provider.answer(query, self.local_results)
                    if answer:
                        GLib.idle_add(self._show_answer, answer, generation)

                threading.Thread(target=answer_work, daemon=True).start()

        def _web_search_done(
            self,
            query: str,
            results: list[SearchResult],
            generation: int,
        ) -> bool:
            if generation != self.search_generation:
                return False
            self.web_results = results
            self._render_sections()
            local_count = len(self.local_results)
            web_count = len(self.web_results)
            if web_count:
                self.status.set_text(
                    f"{local_count} yerel ve {web_count} web sonucu bulundu."
                )
            else:
                self.status.set_text(
                    f"{local_count} yerel sonuç bulundu; web sonuçlarına ulaşılamadı."
                )

            if self.provider.available():
                self.ai_badge.set_text(
                    f"● Kaynaklı cevap hazırlanıyor — {self.provider.model}"
                )

                def answer_work() -> None:
                    answer = self.provider.answer_with_sources(
                        query, self.local_results, self.web_results
                    )
                    GLib.idle_add(self._show_general_answer, answer, generation)

                threading.Thread(target=answer_work, daemon=True).start()
            else:
                self.ai_badge.set_text("○ Web sonuçları hazır — yerel model kapalı")
                if not local_count and not web_count:
                    self._show_answer(
                        "Yerel sonuç bulunamadı ve web aramasına ulaşılamadı.",
                        generation,
                    )
            return False

        def _render_sections(self) -> None:
            sectioned: list[SearchResult] = []
            groups = (
                ("İŞLEM", [r for r in self.local_results if r.result_type == "action"]),
                (
                    "UYGULAMALAR",
                    [r for r in self.local_results if r.result_type == "application"],
                ),
                (
                    "BİLGİSAYARIMDA",
                    [r for r in self.local_results if r.result_type == "file"],
                ),
                (
                    "GÜNCEL BİLGİ",
                    [r for r in self.web_results if r.result_type == "live"],
                ),
                (
                    "WEB SONUÇLARI",
                    [r for r in self.web_results if r.result_type == "web"],
                ),
            )
            for title, items in groups:
                if not items:
                    continue
                sectioned.append(
                    SearchResult(
                        result_type="section",
                        title=title,
                        subtitle="",
                        target="",
                    )
                )
                sectioned.extend(items)
            self._show_results(sectioned)

        def _show_answer(self, answer: str, generation: int) -> bool:
            if generation != self.search_generation:
                return False
            self.detail_title.set_text("SearchPars")
            self.detail_label.set_text(answer)
            self.detail_source.set_text("")
            return False

        def _show_general_answer(self, answer: str | None, generation: int) -> bool:
            if generation != self.search_generation:
                return False
            self.ai_badge.set_text(f"● Yerel yapay zekâ etkin — {self.provider.model}")
            if answer:
                self.detail_title.set_text("Yapay Zekâ Yanıtı")
                self.detail_label.set_text(answer)
                sources = [
                    f"[{index}] {result.title}\n{result.subtitle}"
                    for index, result in enumerate(self.web_results[:6], start=1)
                ]
                self.detail_source.set_text(
                    "KAYNAKLAR\n\n" + "\n\n".join(sources) if sources else ""
                )
                if self.web_results:
                    self.status.set_text("Kaynaklı yapay zekâ cevabı hazır.")
                else:
                    self.status.set_text(
                        "Yapay zekâ cevabı hazır; web kaynağı alınamadı."
                    )
            else:
                self.detail_title.set_text("Yapay Zekâ")
                self.detail_label.set_text(
                    "Yapay zekâ şu anda cevap üretemedi. Biraz sonra tekrar deneyin."
                )
                self.detail_source.set_text("")
                self.status.set_text("Yapay zekâ cevabı alınamadı.")
            return False

        def _show_results(self, results: list[SearchResult]) -> None:
            for child in self.listbox.get_children():
                self.listbox.remove(child)
            self.current_results = results
            for result in results:
                row = Gtk.ListBoxRow()
                row.result = result
                if result.result_type == "section":
                    row.set_selectable(False)
                    row.set_activatable(False)
                    section = Gtk.Label(label=result.title)
                    section.set_xalign(0)
                    section.get_style_context().add_class("section-title")
                    row.add(section)
                    self.listbox.add(row)
                    continue
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
                icon = Gtk.Image.new_from_icon_name(result.icon, Gtk.IconSize.DIALOG)
                box.pack_start(icon, False, False, 0)
                text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
                title = Gtk.Label(label=result.title)
                title.set_xalign(0)
                title.get_style_context().add_class("result-title")
                text_box.pack_start(title, False, False, 0)
                subtitle = Gtk.Label(label=result.subtitle)
                subtitle.set_xalign(0)
                subtitle.set_ellipsize(3)
                subtitle.get_style_context().add_class("result-subtitle")
                text_box.pack_start(subtitle, False, False, 0)
                if result.snippet:
                    snippet = Gtk.Label(label=result.snippet)
                    snippet.set_xalign(0)
                    snippet.set_ellipsize(3)
                    snippet.get_style_context().add_class("result-snippet")
                    text_box.pack_start(snippet, False, False, 0)
                box.pack_start(text_box, True, True, 0)
                row.add(box)
                self.listbox.add(row)
            self.listbox.show_all()
            if results:
                for row in self.listbox.get_children():
                    if row.result.result_type != "section":
                        self.listbox.select_row(row)
                        break

        def _activate_result(self, result: SearchResult) -> None:
            if result.result_type == "section":
                return
            if result.result_type == "action":
                success, message = run_action(result.target)
                self.status.set_text(message)
                if success:
                    self.entry.set_text("")
                return
            try:
                open_target(result)
                self.close()
            except OSError as exc:
                self.status.set_text(f"Açılamadı: {exc}")

        def _row_selected(self, _listbox, row) -> None:
            if row is None or row.result.result_type == "section":
                return
            result = row.result
            self.detail_title.set_text(result.title)
            if result.result_type == "action":
                detail = result.subtitle + "\n\nEnter tuşuyla bu işlemi çalıştır."
            elif result.result_type == "application":
                detail = result.subtitle + "\n\nUygulamayı açmak için Enter tuşuna bas."
            elif result.result_type in {"web", "live"}:
                detail = result.snippet or result.subtitle
            else:
                detail = result.snippet or "Dosyayı açmak için Enter tuşuna bas."
            self.detail_label.set_text(detail)
            self.detail_source.set_text(result.target)

        def _row_activated(self, _listbox, row) -> None:
            self._activate_result(row.result)

        def _activate_selected(self, _entry) -> None:
            row = self.listbox.get_selected_row()
            if row:
                self._activate_result(row.result)

        def _on_key(self, _widget, event) -> bool:
            if event.keyval == Gdk.KEY_Escape:
                self.close()
                return True
            if event.keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
                rows = self.listbox.get_children()
                if not rows:
                    return False
                selected = self.listbox.get_selected_row()
                index = selected.get_index() if selected else 0
                index += 1 if event.keyval == Gdk.KEY_Down else -1
                self.listbox.select_row(rows[max(0, min(index, len(rows) - 1))])
                return True
            return False

    window = SearchParsWindow()
    window.show_all()
    Gtk.main()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SearchPars yapay zekâlı Pardus araması")
    parser.add_argument("--cli", metavar="SORGU", help="Aramayı terminalden çalıştır")
    parser.add_argument("--rebuild", action="store_true", help="Arama dizinini yenile")
    args = parser.parse_args()
    if args.cli:
        return cli(args.cli, rebuild=args.rebuild)
    if args.rebuild:
        index = SearchIndex()
        stats = index.rebuild()
        print(f"{stats.files} dosya ve {stats.applications} uygulama indekslendi.")
        return 0
    return gui()


if __name__ == "__main__":
    raise SystemExit(main())
