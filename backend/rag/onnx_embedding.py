"""Same MiniLM embeddings with bounded CPU memory for small deployments."""
from functools import cached_property
from typing import Any
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2


class LowMemoryMiniLM(ONNXMiniLM_L6_V2):
    """Use Chroma's verified MiniLM export, one document and CPU thread at a time."""

    def _forward(self, documents: list[str], batch_size: int = 1):
        return super()._forward(documents, batch_size=1)

    @cached_property
    def model(self) -> Any:
        options = self.ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        options.enable_mem_pattern = False
        options.log_severity_level = 3
        options.graph_optimization_level = self.ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return self.ort.InferenceSession(
            str(self.DOWNLOAD_PATH / self.EXTRACTED_FOLDER_NAME / "model.onnx"),
            providers=["CPUExecutionProvider"], sess_options=options,
        )
