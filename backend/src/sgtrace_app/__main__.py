"""本地开发入口：python -m sgtrace_app。"""
import uvicorn
from pathlib import Path
from dotenv import load_dotenv


def main():
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    uvicorn.run("sgtrace_app.main:app", host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
