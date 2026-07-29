#!/usr/bin/env python3
"""Kesintiye dayanıklı Ollama model indiricisi.

Ollama'nın paralel parça indiricisi bazı bağlantı hatalarında ilerleme
bilgisini geri alabiliyor. Bu araç her blob'u tek, sıralı bir dosyaya indirir.
curl her yeniden çalıştığında mevcut dosya boyutundan HTTP Range ile devam
eder; tamamlanan dosya SHA-256 ile doğrulanmadan Ollama'ya eklenmez.
"""

from __future__ import annotations

import argparse
import grp
import hashlib
import json
import os
import pwd
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


MANIFEST_MEDIA_TYPE = "application/vnd.docker.distribution.manifest.v2+json"


@dataclass(frozen=True)
class ModelReference:
    registry: str
    namespace: str
    repository: str
    tag: str

    @property
    def manifest_url(self) -> str:
        return (
            f"{self.registry}/v2/{self.namespace}/{self.repository}"
            f"/manifests/{self.tag}"
        )

    def blob_url(self, digest: str) -> str:
        return (
            f"{self.registry}/v2/{self.namespace}/{self.repository}"
            f"/blobs/{digest}"
        )


@dataclass(frozen=True)
class Blob:
    digest: str
    size: int
    media_type: str

    @property
    def algorithm(self) -> str:
        return self.digest.split(":", 1)[0]

    @property
    def hex_digest(self) -> str:
        return self.digest.split(":", 1)[1]

    @property
    def filename(self) -> str:
        return self.digest.replace(":", "-", 1)


def parse_model_reference(
    model: str, registry: str = "https://registry.ollama.ai"
) -> ModelReference:
    raw = model.strip()
    if not raw:
        raise ValueError("Model adı boş olamaz.")

    if ":" in raw.rsplit("/", 1)[-1]:
        name, tag = raw.rsplit(":", 1)
    else:
        name, tag = raw, "latest"

    parts = [part for part in name.split("/") if part]
    if len(parts) == 1:
        namespace, repository = "library", parts[0]
    elif len(parts) == 2:
        namespace, repository = parts
    else:
        raise ValueError(f"Desteklenmeyen model adı: {model}")

    safe_component = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    if not all(
        safe_component.fullmatch(component)
        for component in (namespace, repository, tag)
    ):
        raise ValueError(f"Geçersiz model adı: {model}")

    return ModelReference(
        registry=registry.rstrip("/"),
        namespace=namespace,
        repository=repository,
        tag=tag,
    )


def _human_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(amount)} {unit}"
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"


def _fetch_manifest(
    reference: ModelReference,
    attempts: int,
    retry_wait: float,
    timeout: float = 30,
) -> bytes:
    request = urllib.request.Request(
        reference.manifest_url,
        headers={"Accept": MANIFEST_MEDIA_TYPE, "User-Agent": "SearchPars/0.4.4"},
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
            json.loads(data)
            return data
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            print(
                f"[SearchPars] Model bilgisi alınamadı "
                f"({attempt}/{attempts}): {exc}",
                flush=True,
            )
            if attempt < attempts:
                time.sleep(retry_wait)
    raise RuntimeError(f"Model manifesti indirilemedi: {last_error}")


def _parse_blobs(manifest_data: bytes) -> list[Blob]:
    payload = json.loads(manifest_data)
    candidates: list[dict[str, object]] = []
    config = payload.get("config")
    if isinstance(config, dict):
        candidates.append(config)
    layers = payload.get("layers")
    if isinstance(layers, list):
        candidates.extend(item for item in layers if isinstance(item, dict))

    blobs: list[Blob] = []
    seen: set[str] = set()
    for item in candidates:
        digest = str(item.get("digest", ""))
        size = int(item.get("size", 0))
        media_type = str(item.get("mediaType", ""))
        if not digest.startswith("sha256:") or len(digest) != 71:
            raise ValueError(f"Manifestte geçersiz blob özeti: {digest}")
        if size <= 0:
            raise ValueError(f"Manifestte geçersiz blob boyutu: {digest}")
        if digest not in seen:
            seen.add(digest)
            blobs.append(Blob(digest=digest, size=size, media_type=media_type))

    if not blobs:
        raise ValueError("Manifestte indirilecek model dosyası bulunamadı.")
    return blobs


def _sha256(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_blob(path: Path, blob: Blob, verify_hash: bool = True) -> bool:
    if not path.is_file() or path.stat().st_size != blob.size:
        return False
    return not verify_hash or _sha256(path) == blob.hex_digest


def _completed_bytes(blobs_dir: Path, blobs: Iterable[Blob]) -> int:
    completed = 0
    for blob in blobs:
        final_path = blobs_dir / blob.filename
        partial_path = blobs_dir / f"{blob.filename}.searchpars-part"
        if final_path.is_file() and final_path.stat().st_size == blob.size:
            completed += blob.size
        elif partial_path.is_file():
            completed += min(partial_path.stat().st_size, blob.size)
    return completed


def _print_progress(blobs_dir: Path, blobs: list[Blob]) -> None:
    total = sum(blob.size for blob in blobs)
    completed = _completed_bytes(blobs_dir, blobs)
    percentage = completed * 100 / total if total else 100
    print(
        f"[SearchPars] Gerçek model ilerlemesi: "
        f"{_human_bytes(completed)} / {_human_bytes(total)} "
        f"(%{percentage:.1f})",
        flush=True,
    )


def _curl_command(url: str, partial_path: Path) -> list[str]:
    return [
        "curl",
        "--fail",
        "--location",
        "--continue-at",
        "-",
        "--connect-timeout",
        "30",
        "--speed-limit",
        "1024",
        "--speed-time",
        "120",
        "--silent",
        "--show-error",
        "--header",
        f"Accept: {MANIFEST_MEDIA_TYPE}",
        "--output",
        str(partial_path),
        url,
    ]


def _download_blob(
    reference: ModelReference,
    blob: Blob,
    blobs: list[Blob],
    blobs_dir: Path,
    attempts: int,
    retry_wait: float,
    popen_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
) -> None:
    final_path = blobs_dir / blob.filename
    partial_path = blobs_dir / f"{blob.filename}.searchpars-part"

    if _valid_blob(final_path, blob):
        _print_progress(blobs_dir, blobs)
        return

    if final_path.exists():
        raise RuntimeError(
            f"Bozuk veya eksik model blob'u bulundu: {final_path}. "
            "Dosya otomatik silinmedi."
        )
    if partial_path.exists() and partial_path.stat().st_size > blob.size:
        raise RuntimeError(
            f"Kısmi model dosyası beklenenden büyük: {partial_path}. "
            "Dosya otomatik silinmedi."
        )

    for attempt in range(1, attempts + 1):
        existing = partial_path.stat().st_size if partial_path.exists() else 0
        print(
            f"[SearchPars] {blob.digest[7:19]} indiriliyor; "
            f"kayıtlı bölüm {_human_bytes(existing)} "
            f"({attempt}/{attempts})",
            flush=True,
        )
        process = popen_factory(
            _curl_command(reference.blob_url(blob.digest), partial_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            while process.poll() is None:
                _print_progress(blobs_dir, blobs)
                time.sleep(2)
            _, error_output = process.communicate()
        except (KeyboardInterrupt, SystemExit):
            process.send_signal(signal.SIGINT)
            process.wait()
            print(
                "[SearchPars] İndirme durduruldu; tamamlanan bölüm korundu.",
                flush=True,
            )
            raise

        current = partial_path.stat().st_size if partial_path.exists() else 0
        _print_progress(blobs_dir, blobs)
        if process.returncode == 0 and current == blob.size:
            print(
                f"[SearchPars] {blob.digest[7:19]} SHA-256 ile doğrulanıyor",
                flush=True,
            )
            if _sha256(partial_path) != blob.hex_digest:
                raise RuntimeError(
                    f"Model blob'u doğrulanamadı: {partial_path}. "
                    "Dosya otomatik silinmedi."
                )
            os.replace(partial_path, final_path)
            return

        error_text = error_output.decode("utf-8", errors="replace").strip()
        if process.returncode == 33:
            raise RuntimeError(
                "Model sunucusu HTTP devam isteğini kabul etmedi; "
                "mevcut kısmi dosya korunuyor."
            )
        if process.returncode == 0 and current > blob.size:
            raise RuntimeError(
                f"İndirilen dosya beklenenden büyük: {partial_path}"
            )
        print(
            f"[SearchPars] Bağlantı kesildi; {_human_bytes(current)} korundu."
            + (f" curl: {error_text}" if error_text else ""),
            flush=True,
        )
        if attempt < attempts:
            time.sleep(retry_wait)

    raise RuntimeError(
        f"{blob.digest[7:19]} indirilemedi; kısmi dosya silinmedi."
    )


def _set_owner(paths: Iterable[Path], owner: str | None) -> None:
    if not owner:
        return
    user = pwd.getpwnam(owner)
    try:
        group = grp.getgrnam(owner)
        gid = group.gr_gid
    except KeyError:
        gid = user.pw_gid
    for path in paths:
        os.chown(path, user.pw_uid, gid)


def install_model(
    model: str,
    models_dir: Path,
    registry: str = "https://registry.ollama.ai",
    attempts: int = 50,
    retry_wait: float = 5,
    owner: str | None = None,
    manifest_data: bytes | None = None,
) -> None:
    if shutil.which("curl") is None:
        raise RuntimeError("curl bulunamadı.")

    reference = parse_model_reference(model, registry)
    models_dir = models_dir.resolve()
    blobs_dir = models_dir / "blobs"
    manifest_dir = (
        models_dir
        / "manifests"
        / reference.registry.split("://", 1)[-1]
        / reference.namespace
        / reference.repository
    )
    blobs_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    if manifest_data is None:
        print("[SearchPars] Model manifesti alınıyor", flush=True)
        manifest_data = _fetch_manifest(reference, attempts, retry_wait)
    blobs = _parse_blobs(manifest_data)

    print(
        "[SearchPars] İndirme kalıcı dosyalara yapılıyor; bağlantı kesilse "
        "bile yüzde geriye dönmez.",
        flush=True,
    )
    _print_progress(blobs_dir, blobs)
    for blob in blobs:
        _download_blob(
            reference,
            blob,
            blobs,
            blobs_dir,
            attempts,
            retry_wait,
        )

    manifest_path = manifest_dir / reference.tag
    manifest_tmp = manifest_dir / f".{reference.tag}.searchpars-tmp"
    manifest_tmp.write_bytes(manifest_data)
    os.replace(manifest_tmp, manifest_path)

    owned_paths = [blobs_dir, manifest_dir, manifest_path]
    owned_paths.extend(blobs_dir / blob.filename for blob in blobs)
    _set_owner(owned_paths, owner)
    _print_progress(blobs_dir, blobs)
    print(f"[SearchPars] Model dosyaları hazır: {model}", flush=True)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--models-dir", type=Path, required=True)
    parser.add_argument(
        "--registry", default="https://registry.ollama.ai"
    )
    parser.add_argument("--attempts", type=int, default=50)
    parser.add_argument("--retry-wait", type=float, default=5)
    parser.add_argument("--owner")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        install_model(
            model=args.model,
            models_dir=args.models_dir,
            registry=args.registry,
            attempts=args.attempts,
            retry_wait=args.retry_wait,
            owner=args.owner,
        )
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"[SearchPars] Model kurulumu başarısız: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
