import fitz
import requests
import urllib
import tempfile
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
import uvicorn


app = FastAPI()

class TemplateElementPosition(BaseModel):
    x: int
    y: int
    w: int
    h: int

class TemplateElement(BaseModel):
    content: str
    element_type: str
    pos: TemplateElementPosition

class PosterRequest(BaseModel):
    template_url: str
    elements: list[TemplateElement]

async def get_tmp_file():
    tmpFile = tempfile.NamedTemporaryFile("wb+")
    try:
        yield tmpFile
    finally:
        tmpFile.close()

@app.post("/poster/", response_class=Response)
def insertQR(poster: PosterRequest, tmpFile: Annotated[str, Depends(get_tmp_file)]):
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
            qrURL = f'https://api.qrserver.com/v1/create-qr-code/?size={el.pos.w}x{el.pos.h}&data={urllib.parse.quote_plus(el.content)}&format=jpg'
            resp = requests.get(qrURL)
            if resp.status_code != 200:
                raise HTTPException(419, {"message": "invalid poster url"}) 
            # define the position (upper-right corner)
            image_rectangle = fitz.Rect(el.pos.x,el.pos.y,el.pos.x+el.pos.w,el.pos.y+el.pos.h)
            # add the image
            first_page.insert_image(image_rectangle, stream=resp.content)
        elif el.element_type == "text":
            shape = first_page.new_shape()
            # define the position 
            image_rectangle = fitz.Rect(el.pos.x,el.pos.y,el.pos.x+el.pos.w,el.pos.y+el.pos.h)
            shape.insert_textbox(image_rectangle, el.content, fontname="hebo", color=fitz.pdfcolor["black"], rotate=0)
            shape.commit()
    return Response(file_handle.write(), media_type="application/pdf")  

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, loop="uvloop")
