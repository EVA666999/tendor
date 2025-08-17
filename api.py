"""
FastAPI endpoint для парсера тендеров B2B-Center.
"""

from fastapi import FastAPI, HTTPException
from main import B2BCenterParser

app = FastAPI(title="B2B-Center Parser API")

parser = B2BCenterParser()


@app.get("/tenders")
async def get_tenders(max_tenders: int = 100):
    """Получить тендеры с сайта B2B-Center."""
    try:
        max_tenders = min(max_tenders, 1000)

        tenders = await parser.get_tenders(limit=max_tenders)

        result = []
        for tender in tenders:
            result.append(
                {
                    "title": tender.title,
                    "company": tender.company,
                    "date_created": tender.date_created,
                    "date_deadline": tender.date_deadline,
                    "url": tender.url,
                    "category": tender.category,
                    "description": tender.description,
                }
            )

        return {"success": True, "count": len(result), "tenders": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
