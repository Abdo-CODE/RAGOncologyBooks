from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance,VectorParams


class QdrantStorage:
    def __init__(self, url="http://localhost:6333", collection="docs",dim=384):
        self.client = QdrantClient(url=url,timeout=30)
        self.collection_name = collection
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )

    def upsert(self, id, vector, payload):
        points = [PointStruct(id=id[i], vector=vector[i], payload=payload[i]) for i in range(len(id))]
        self.client.upsert(collection_name=self.collection_name, points=points)

    def search(self,query_vector, top_k=5):
        results=self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k
        ).points
        contexts=[]
        sources=set()
        for r in results:
            payload=getattr(r, "payload", None) or {}
            text=payload.get("text", "")  
            source=payload.get("source" ,"")
            if text:
                contexts.append(text)
                sources.add(source)
        return {"contexts": contexts, "sources": list(sources)}