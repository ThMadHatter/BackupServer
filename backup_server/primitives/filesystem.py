import sh
import hashlib
from pathlib import Path
from typing import Any, Dict
from backup_server.primitives.base import Primitive, PrimitiveContract

class Tar(Primitive):
    contract = PrimitiveContract(
        inputs=["source_dir", "dest_file", "compression"],
        outputs=["dest_file"],
        side_effects=["creates_tar_archive"],
        failure_modes=["filesystem_full", "permission_denied"],
        retryable=False,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        source_dir = self.options.get("source_dir")
        dest_file = self.options.get("dest_file")
        compression = self.options.get("compression", "zstd")

        self.logger.info("Executing Tar", source=source_dir, dest=dest_file, compression=compression)

        args = ["-cvf", str(dest_file), "-C", str(source_dir), "."]
        if compression == "zstd":
            args.insert(0, "-I")
            args.insert(1, "zstd")
        elif compression == "gzip":
            args.insert(0, "-z")
        # 'none' or other values will just be a normal tar

        sh.tar(*args)
        return dest_file

class Copy(Primitive):
    contract = PrimitiveContract(
        inputs=["source", "dest"],
        outputs=["dest"],
        side_effects=["copies_files"],
        failure_modes=["filesystem_full", "permission_denied"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        source = self.options.get("source")
        dest = self.options.get("dest")

        self.logger.info("Executing Copy", source=source, dest=dest)
        if Path(source).is_dir():
            sh.cp("-r", str(source), str(dest))
        else:
            sh.cp(str(source), str(dest))
        return dest

class Compress(Primitive):
    contract = PrimitiveContract(
        inputs=["source", "algorithm"],
        outputs=["compressed_file"],
        side_effects=["creates_compressed_file"],
        failure_modes=["filesystem_full", "unsupported_algorithm"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        source = self.options.get("source")
        algorithm = self.options.get("algorithm", "zstd")

        self.logger.info("Executing Compress", source=source, algorithm=algorithm)
        if algorithm == "zstd":
            sh.zstd(str(source))
            return f"{source}.zst"
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")

class Checksum(Primitive):
    contract = PrimitiveContract(
        inputs=["file_path", "algorithm"],
        outputs=["checksum"],
        side_effects=[],
        failure_modes=["file_not_found"],
        retryable=True,
        idempotent=True
    )

    def execute(self, context: Dict[str, Any]) -> Any:
        file_path = self.options.get("file_path")
        algorithm = self.options.get("algorithm", "sha256")

        self.logger.info("Executing Checksum", file=file_path, algorithm=algorithm)

        hash_func = getattr(hashlib, algorithm)()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                hash_func.update(byte_block)

        return hash_func.hexdigest()
