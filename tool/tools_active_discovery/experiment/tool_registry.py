import os
import json
import numpy as np
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from langchain_core.tools import BaseTool, StructuredTool

class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.tool_descriptions = []
        self.tool_names = []
        self.embeddings_matrix = None
        self._is_fitted = False
        self.api_key = os.getenv("SILICONFLOW_API_KEY")
        self.api_base = os.getenv("SILICONFLOW_API_BASE") or "https://api.siliconflow.cn/v1"
        self.embedding_model = os.getenv("SILICONFLOW_EMBEDDING_MODEL") or "Qwen/Qwen3-Embedding-4B"
        self.embedding_dims = int(os.getenv("SILICONFLOW_EMBEDDING_DIMS") or "1024")

    def register_tools(self, tools):
        for tool in tools:
            self.tools[tool.name] = tool
            desc = f"{tool.name}: {tool.description}"
            if getattr(tool, "args", None):
                desc += f" Arguments: {json.dumps(tool.args)}"
            ln = tool.name.lower()
            if ("finance" in ln) or ("yfinance" in ln) or ("stock" in ln):
                desc += " Keywords: finance stock market quote ticker price equities"
            self.tool_descriptions.append(desc)
            self.tool_names.append(tool.name)
        if self.tool_descriptions:
            try:
                embs = self._embed_texts(self.tool_descriptions)
                norms = np.linalg.norm(embs, axis=1, keepdims=True)
                norms[norms == 0] = 1.0
                self.embeddings_matrix = embs / norms
                self._is_fitted = True
            except Exception:
                self.embeddings_matrix = None
                self._is_fitted = False

    def search(self, query, top_k=5):
        names = self.tool_names
        descs = self.tool_descriptions
        ql = query.lower()
        kw_scores = []
        for i in range(len(names)):
            t = (names[i] + " " + descs[i]).lower()
            s = 0
            if "stock" in ql and "stock" in t:
                s += 2
            if "finance" in ql and "finance" in t:
                s += 2
            if "price" in ql and "price" in t:
                s += 1
            if "market" in ql and "market" in t:
                s += 1
            if "ticker" in ql and "ticker" in t:
                s += 1
            if "quote" in ql and "quote" in t:
                s += 1
            kw_scores.append(float(s))
        if self._is_fitted and self.embeddings_matrix is not None:
            try:
                vecs = self._embed_texts([query])
                v = vecs[0]
                n = np.linalg.norm(v)
                sims = np.zeros(len(names), dtype=np.float32) if n == 0 else np.dot(self.embeddings_matrix, v / n)
                scores = 0.7 * sims + 0.3 * np.array(kw_scores, dtype=np.float32)
            except Exception:
                scores = np.array(kw_scores, dtype=np.float32)
        else:
            scores = np.array(kw_scores, dtype=np.float32)
        idxs = np.argsort(scores)[-top_k:][::-1]
        res = []
        for idx in idxs:
            name = names[idx]
            res.append(self.tools[name])
        return res

    def get_tool(self, name):
        return self.tools.get(name)

    def get_all_tools(self):
        return list(self.tools.values())

    def _embed_texts(self, texts):
        if not self.api_key:
            raise RuntimeError("SILICONFLOW_API_KEY is not set")
        url = self.api_base.rstrip("/") + "/embeddings"
        payload = {
            "model": self.embedding_model,
            "input": texts,
            "dimensions": self.embedding_dims
        }
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        try:
            with urlopen(req) as resp:
                body = resp.read().decode("utf-8")
        except HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}")
        except URLError as e:
            raise RuntimeError(str(e))
        obj = json.loads(body)
        if isinstance(obj, dict) and "data" in obj:
            arr = [item.get("embedding") or item.get("vector") for item in obj["data"]]
        elif isinstance(obj, dict) and "embeddings" in obj:
            arr = obj["embeddings"]
        else:
            raise RuntimeError("Invalid embeddings response")
        return np.array(arr, dtype=np.float32)
