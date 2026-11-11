"""Build a new, uniquely named evaluation index and record it in index.json."""

import asyncio
import uuid

from common import FIXTURE, MANIFEST, credentials, digest, read, write
from moss import DocumentInfo, MossClient


async def main():
    project, key = credentials()
    docs = read(FIXTURE)["documents"]
    name = "onboarding-eval-" + uuid.uuid4().hex[:12]
    manifest = {
        "index": name,
        "project": digest(project),
        "documents": digest(docs),
        "state": "pending",
        "embedding_model": "moss-minilm",
    }
    # Exclusive creation prevents two seeds in this folder racing to create indexes.
    with MANIFEST.open("x", encoding="utf-8") as out:
        import json

        json.dump(manifest, out)
    print("Creating test index", name, flush=True)
    async with MossClient(project, key) as client:
        await client.create_index(
            name,
            [DocumentInfo(**doc) for doc in docs],
            manifest["embedding_model"],
            wait=True,
        )
    manifest["state"] = "ready"
    write(MANIFEST, manifest)
    print("Ready:", name)


if __name__ == "__main__":
    asyncio.run(main())
