from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import shutil, os, sys
from pathlib import Path
from datetime import datetime
import geopandas as gpd
import numpy as np
from PIL import Image

# GeoDeep 경로 설정 및 run() 호출
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "GeoDeep", "geodeep", "scripts")))
from main import run
from geodeep.segmentation import save_mask_to_raster, simplify_polygon, mask_to_gdf
from src.core.building_change_detection.detect_building_change import cd_pipeline

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

BASE_UPLOAD_DIR = Path("app/static/uploads")
BASE_RESULT_DIR = Path("app/static/results")
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
BASE_RESULT_DIR.mkdir(parents=True, exist_ok=True)

def geojson_to_shp(input_geojson: Path, output_dir: Path) -> Path:
    gdf = gpd.read_file(input_geojson)
    shp_path = output_dir / "converted.shp"
    gdf.to_file(shp_path, driver="ESRI Shapefile")
    return shp_path

@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request, "result": None})

@app.post("/detect_from_image", response_class=HTMLResponse)
async def detect_from_image(
    request: Request,
    geotiff_file: UploadFile = File(...),
    past_geojson_file: UploadFile = File(...),
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
    geojson_path = upload_dir / past_geojson_file.filename
    with open(geotiff_path, "wb") as f:
        shutil.copyfileobj(geotiff_file.file, f)
    with open(geojson_path, "wb") as f:
        shutil.copyfileobj(past_geojson_file.file, f)

    # ✅ GeoJSON → SHP
    past_shp_path = geojson_to_shp(geojson_path, upload_dir)

    # ✅ 모델 추론
    model_path = "GeoDeep/model/building_2005_deepness.onnx"
    result = run(str(geotiff_path), model_path, resolution=resolution)
    output = result[0] if isinstance(result, tuple) else result
    gdf = result[1] if isinstance(result, tuple) else mask_to_gdf(output, geotiff_path)
    gdf = simplify_polygon(gdf, tolerance=0.5, preserve_topology=True)

    # 저장
    mask_tif_path = result_dir / "mask_output.tif"
    save_mask_to_raster(str(geotiff_path), output, str(mask_tif_path))
    Image.fromarray((output * 255).astype(np.uint8)).save(result_dir / "mask_preview.png")

    current_shp_path = upload_dir / "current_building.shp"
    gdf.to_file(current_shp_path)

    # 변화탐지 실행
    dmap_dir, seg_dir = result_dir / "dmap", result_dir / "seg"
    dmap_dir.mkdir(), seg_dir.mkdir()
    cd_pipeline(
        dmap_path=str(past_shp_path),
        seg_path=str(current_shp_path),
        dmap_output_path=str(dmap_dir),
        seg_output_path=str(seg_dir),
        cut_threshold=cut_threshold,
        cd_threshold=cd_threshold,
    )

    # SHP → GeoJSON
    dmap_geojson_path = result_dir / "dmap_result.geojson"
    seg_geojson_path = result_dir / "seg_result.geojson"
    gpd.read_file(dmap_dir / "dmap.shp").to_file(dmap_geojson_path, driver="GeoJSON")
    gpd.read_file(seg_dir / "seg.shp").to_file(seg_geojson_path, driver="GeoJSON")

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "result": {
            "resolution": resolution,
            "cut_threshold": cut_threshold,
            "cd_threshold": cd_threshold,
            "mask_image": f"/static/results/{session_id}/mask_preview.png",
            "dmap": f"/download/{session_id}/dmap_result.geojson",
            "seg": f"/download/{session_id}/seg_result.geojson"
        }
    })

@app.get("/download/{session_id}/{filename}")
async def download_file(session_id: str, filename: str):
    file_path = BASE_RESULT_DIR / session_id / filename
    return FileResponse(path=file_path, filename=filename)
