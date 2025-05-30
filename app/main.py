from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import shutil
import zipfile
from pathlib import Path
from datetime import datetime
import numpy as np
from PIL import Image

# ✅ GeoDeep/scripts/main.py 안의 run() 직접 사용하도록 import
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "GeoDeep", "geodeep", "scripts")))
from main import run  # ← 수정된 run() 함수

from geodeep.segmentation import save_mask_to_raster, simplify_polygon, mask_to_gdf
from src.core.building_change_detection.detect_building_change import cd_pipeline

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

BASE_UPLOAD_DIR = Path("app/static/uploads")
BASE_RESULT_DIR = Path("app/static/results")
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BASE_RESULT_DIR.mkdir(parents=True, exist_ok=True)


def zip_folder(folder_path: Path, zip_name: str):
    zip_path = folder_path.parent / zip_name
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file in folder_path.glob("*"):
            if file.is_file():
                zf.write(file, arcname=file.name)
    return zip_path.name


@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "result": None})


@app.post("/detect_from_image", response_class=HTMLResponse)
async def detect_from_image(
        request: Request,
        geotiff_file: UploadFile = File(...),
        past_shp_zip: UploadFile = File(...),
        resolution: float = Form(20.0),
        cut_threshold: float = Form(0.05),
        cd_threshold: float = Form(0.7)
):
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir = BASE_UPLOAD_DIR / session_id
    result_dir = BASE_RESULT_DIR / session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    geotiff_path = upload_dir / geotiff_file.filename
    past_shp_zip_path = upload_dir / past_shp_zip.filename
    past_shp_dir = upload_dir / "past_shp"
    past_shp_dir.mkdir(exist_ok=True)

    with open(geotiff_path, "wb") as f:
        shutil.copyfileobj(geotiff_file.file, f)
    with open(past_shp_zip_path, "wb") as f:
        shutil.copyfileobj(past_shp_zip.file, f)

    with zipfile.ZipFile(past_shp_zip_path, 'r') as zip_ref:
        zip_ref.extractall(past_shp_dir)
    past_shp_file = list(past_shp_dir.glob("*.shp"))[0]

    # ✅ 고정된 모델 경로 사용
    model_path = "GeoDeep/model/building_2005_deepness.onnx"

    result = run(str(geotiff_path), model_path, resolution=resolution)

    if isinstance(result, tuple) and len(result) == 2:
        output, gdf = result
    else:
        output = result
        gdf = mask_to_gdf(output, geotiff_path)
        gdf = simplify_polygon(gdf, tolerance=0.5, preserve_topology=True)

    mask_tif_path = result_dir / "mask_output.tif"
    save_mask_to_raster(str(geotiff_path), output, str(mask_tif_path))

    png_preview_path = result_dir / "mask_preview.png"
    img = Image.fromarray((output * 255).astype(np.uint8))
    img.save(png_preview_path)

    current_shp_path = upload_dir / "current_detected_buildings.shp"
    gdf.to_file(current_shp_path, driver="ESRI Shapefile")

    dmap_result_dir = result_dir / "dmap"
    seg_result_dir = result_dir / "seg"
    dmap_result_dir.mkdir(exist_ok=True)
    seg_result_dir.mkdir(exist_ok=True)

    cd_pipeline(
        dmap_path=str(past_shp_file),
        seg_path=str(current_shp_path),
        dmap_output_path=str(dmap_result_dir),
        seg_output_path=str(seg_result_dir),
        cut_threshold=cut_threshold,
        cd_threshold=cd_threshold,
    )

    dmap_zip_name = zip_folder(dmap_result_dir, "dmap_result.zip")
    seg_zip_name = zip_folder(seg_result_dir, "seg_result.zip")

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "result": {
            "resolution": resolution,
            "cut_threshold": cut_threshold,
            "cd_threshold": cd_threshold,
            "mask_image": f"/static/results/{session_id}/mask_preview.png",
            "dmap": f"/download/{session_id}/{dmap_zip_name}",
            "seg": f"/download/{session_id}/{seg_zip_name}"
        }
    })


@app.get("/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    file_path = BASE_RESULT_DIR / session_id / filename
    return FileResponse(path=file_path, filename=filename)
