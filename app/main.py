from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
from src.core.building_change_detection.detect_building_change import cd_pipeline

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")

BASE_UPLOAD_DIR = Path("app/static/uploads")
BASE_RESULT_DIR = Path("app/static/results")
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BASE_RESULT_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "result": None})

@app.post("/detect", response_class=HTMLResponse)
async def detect_building_change(
    request: Request,
    dmap_zip: UploadFile = File(...),
    seg_zip: UploadFile = File(...),
    cut_threshold: float = Form(0.05),
    cd_threshold: float = Form(0.7)
):
    # 1. 세션 디렉토리 생성 (날짜+시간 기반)
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = BASE_UPLOAD_DIR / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    dmap_folder = upload_dir / "dmap"
    seg_folder = upload_dir / "seg"
    dmap_folder.mkdir(parents=True, exist_ok=True)
    seg_folder.mkdir(parents=True, exist_ok=True)

    result_dir = BASE_RESULT_DIR / session_id
    dmap_result_dir = result_dir / "dmap"
    seg_result_dir = result_dir / "seg"
    dmap_result_dir.mkdir(parents=True, exist_ok=True)
    seg_result_dir.mkdir(parents=True, exist_ok=True)

    # 2. 업로드 파일 저장
    dmap_zip_path = upload_dir / dmap_zip.filename
    seg_zip_path = upload_dir / seg_zip.filename

    with open(dmap_zip_path, "wb") as f:
        shutil.copyfileobj(dmap_zip.file, f)
    with open(seg_zip_path, "wb") as f:
        shutil.copyfileobj(seg_zip.file, f)

    # 3. 압축 해제
    with zipfile.ZipFile(dmap_zip_path, 'r') as zip_ref:
        zip_ref.extractall(dmap_folder)
    with zipfile.ZipFile(seg_zip_path, 'r') as zip_ref:
        zip_ref.extractall(seg_folder)

    # 4. 입력 shp 추출
    dmap_input = list(dmap_folder.glob("*.shp"))[0]
    seg_input = list(seg_folder.glob("*.shp"))[0]
    dmap_output = dmap_result_dir / "dmap_output.shp"
    seg_output = seg_result_dir / "seg_output.shp"

    # 5. 변화탐지 실행
    cd_pipeline(
        dmap_path=str(dmap_input),
        seg_path=str(seg_input),
        dmap_output_path=str(dmap_output),
        seg_output_path=str(seg_output),
        cut_threshold=cut_threshold,
        cd_threshold=cd_threshold
    )

    # 6. 폴더 압축 함수
    def zip_folder(folder_path: Path, zip_name: str):
        zip_path = folder_path / zip_name
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for file in folder_path.glob("*"):
                if file.is_file():
                    zf.write(file, arcname=file.name)
        return zip_path.name

    dmap_zip_name = zip_folder(dmap_result_dir, "dmap_result.zip")
    seg_zip_name = zip_folder(seg_result_dir, "seg_result.zip")

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "result": {
            "dmap": f"/download/{session_id}/dmap/{dmap_zip_name}",
            "seg": f"/download/{session_id}/seg/{seg_zip_name}",
            "cut_threshold": cut_threshold,
            "cd_threshold": cd_threshold
        }
    })

@app.get("/download/{session_id}/{category}/{filename}")
async def download_file(session_id: str, category: str, filename: str):
    file_path = BASE_RESULT_DIR / session_id / category / filename
    return FileResponse(path=file_path, filename=filename)
