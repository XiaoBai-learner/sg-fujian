"""本地开发入口：python -m sgtrace_app。"""
import uvicorn


def main():
    uvicorn.run("sgtrace_app.main:app", host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
