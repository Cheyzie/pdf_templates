import fitz
import requests
import tempfile
from typing import Annotated, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
import uvicorn
from .services.qr import QRBuilder

app = FastAPI()

class QRStyles(BaseModel):
    logo_url: str | None = Field(default=None)
    style: Optional[str] = Field(default=None)
    eyes_style: Optional[str] = Field(default=None)
    main_color: tuple[int, int, int]= Field(default=(0,0,0))
    bg_color: tuple[int, int, int]= Field(default=(255,255,255))
    inner_eye_color: tuple[int, int, int]= Field(default=(0,0,0))
    outer_eye_color: tuple[int, int, int]= Field(default=(0,0,0))

class TextStyles(BaseModel):
    fontsize: int = Field(default=14)
    color: tuple[int, int, int]= Field(default=(0,0,0))

class TemplateElementPosition(BaseModel):
    x: int
    y: int
    w: int
    h: int

class TemplateElement(BaseModel):
    content: str
    element_type: str
    pos: TemplateElementPosition
    qr_styles: QRStyles = Field(default=QRStyles())
    text_styles: TextStyles = Field(default=TextStyles())

class PosterRequest(BaseModel):
    template_url: str
    elements: list[TemplateElement]

class QRRequest(BaseModel):
    url: str
    qr_styles: QRStyles = Field(default=QRStyles())

def get_tmp_file(suffix: str):
    async def inner():
        tmpFile = tempfile.NamedTemporaryFile("wb+", suffix=suffix)
        try:
            yield tmpFile
        finally:
            tmpFile.close()
    return inner

@app.post("/poster/", response_class=Response)
def insert_qr(poster: PosterRequest, tmpFile: Annotated[str, Depends(get_tmp_file(".pdf"))]):
    qr_builder = QRBuilder()
    resp = requests.get(poster.template_url)
    if resp.status_code != 200:
        raise HTTPException(419, {"message": "invalid poster url"}) 
    
    tmpFile.write(resp.content)

    # retrieve the first page of the PDF
    try:
        file_handle = fitz.open(tmpFile.name)
        first_page = file_handle[0]
    except:
        raise HTTPException(419, {"message": "invalid poster file"}) 

    for el in poster.elements:
        if el.element_type == "qr":
            qr = qr_builder.make_qr(
                el.content,
                logo_url=el.qr_styles.logo_url,
                style=el.qr_styles.style,
                eyes_style=el.qr_styles.eyes_style,
                main_color=el.qr_styles.main_color,
                bg_color=el.qr_styles.bg_color,
                inner_eye_color=el.qr_styles.inner_eye_color,
                outer_eye_color=el.qr_styles.outer_eye_color
                )
            # define the position (upper-right corner)
            image_rectangle = fitz.Rect(el.pos.x,el.pos.y,el.pos.x+el.pos.w,el.pos.y+el.pos.h)
            # add the image
            first_page.insert_image(image_rectangle, stream=qr)
        elif el.element_type == "text":
            shape = first_page.new_shape()
            # define the position 
            image_rectangle = fitz.Rect(el.pos.x,el.pos.y,el.pos.x+el.pos.w,el.pos.y+el.pos.h)
            shape.insert_textbox(image_rectangle, el.content, fontname="hebo", fontsize=float(el.text_styles.fontsize), color=tuple(float(c)/255 for c in el.text_styles.color), rotate=0)
            shape.commit()
    return Response(file_handle.write(), status_code=201, media_type="application/pdf")  

@app.post("/qr/")
def makeQR(qr: QRRequest):
    qr_builder = QRBuilder()
    qr = qr_builder.make_qr(
                qr.url,
                logo_url=qr.qr_styles.logo_url,
                style=qr.qr_styles.style,
                eyes_style=qr.qr_styles.eyes_style,
                main_color=qr.qr_styles.main_color,
                bg_color=qr.qr_styles.bg_color,
                inner_eye_color=qr.qr_styles.inner_eye_color,
                outer_eye_color=qr.qr_styles.outer_eye_color
                )
    return Response(qr, status_code=201, media_type="image/png")  


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, loop="uvloop")
