from typing import Dict
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import SquareModuleDrawer, GappedSquareModuleDrawer, RoundedModuleDrawer, CircleModuleDrawer, VerticalBarsDrawer, HorizontalBarsDrawer
from  qrcode.image.styles.colormasks import SolidFillColorMask
import qrcode
from PIL import Image, ImageDraw
import requests
import io


class QRBuilder:

    __shape_styles = {
        "square":  SquareModuleDrawer,
        "gapped_square": GappedSquareModuleDrawer,
        "rounded": RoundedModuleDrawer,
        "circle": CircleModuleDrawer,
        "vertical_bars": VerticalBarsDrawer,
        "horizontal_bars": HorizontalBarsDrawer
    }

    __eye_shape_styles = {
        "square":  SquareModuleDrawer,
        "gapped_square": SquareModuleDrawer,
        "rounded": RoundedModuleDrawer,
        "circle": RoundedModuleDrawer,
        "vertical_bars": RoundedModuleDrawer,
        "horizontal_bars": RoundedModuleDrawer
    }

    def style_inner_eyes(self, img):
        img_size = img.size[0]
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((60, 60, 90, 90), fill=255) #top left eye
        draw.rectangle((img_size-90, 60, img_size-60, 90), fill=255) #top right eye
        draw.rectangle((60, img_size-90, 90, img_size-60), fill=255) #bottom left eye
        return mask

    def style_outer_eyes(self, img):
        img_size = img.size[0]
        mask = Image.new('L', img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle((40, 40, 110, 110), fill=255) #top left eye
        draw.rectangle((img_size-110, 40, img_size-40, 110), fill=255) #top right eye
        draw.rectangle((40, img_size-110, 110, img_size-40), fill=255) #bottom left eye
        draw.rectangle((60, 60, 90, 90), fill=0) #top left eye
        draw.rectangle((img_size-90, 60, img_size-60, 90), fill=0) #top right eye
        draw.rectangle((60, img_size-90, 90, img_size-60), fill=0) #bottom left eye  
        return mask

    def add_corners(self, im, rad):
        circle = Image.new('L', (rad * 2, rad * 2), 0)
        draw = ImageDraw.Draw(circle)
        draw.ellipse((0, 0, rad * 2 - 1, rad * 2 - 1), fill=255)
        alpha = Image.new('L', im.size, 255)
        w, h = im.size
        alpha.paste(circle.crop((0, 0, rad, rad)), (0, 0))
        alpha.paste(circle.crop((0, rad, rad, rad * 2)), (0, h - rad))
        alpha.paste(circle.crop((rad, 0, rad * 2, rad)), (w - rad, 0))
        alpha.paste(circle.crop((rad, rad, rad * 2, rad * 2)), (w - rad, h - rad))
        im.putalpha(alpha)
        return im

    def make_qr(
            self,
            url: str,
            /,
            *,
            logo_url:str = None,
            style: str = "square",
            eyes_style:str = "square",
            main_color: tuple[int, int, int] = (0, 0, 0),
            bg_color: tuple[int, int, int] = (255, 255, 255),
            inner_eye_color: tuple[int, int, int] = (0, 0, 0),
            outer_eye_color: tuple[int, int, int] = (0, 0, 0)
            ) -> bytes:
        logo = None

        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)

        qr.add_data(url)

        drawer = SquareModuleDrawer()
        eyes_drawer = SquareModuleDrawer()

        if style in self.__shape_styles:
            drawer = self.__shape_styles[style]()
        if eyes_style in self.__shape_styles:   
            eyes_drawer = self.__shape_styles[eyes_style]()


        qr_inner_eyes_img = qr.make_image(image_factory=StyledPilImage,
                                    eye_drawer=eyes_drawer,
                                    color_mask=SolidFillColorMask(back_color=bg_color, front_color=inner_eye_color))

        qr_outer_eyes_img = qr.make_image(image_factory=StyledPilImage,
                                    eye_drawer=eyes_drawer,
                                    color_mask=SolidFillColorMask(back_color=bg_color, front_color=outer_eye_color))

        if logo_url is not None:
            resp = requests.get(logo_url)
            # https://drive.usercontent.google.com/download?id=1F9guy0NfhvuFUE50G0nGlCFwKTsqW7_v&export=download
            if resp.status_code == 200:
                logo = Image.open(io.BytesIO(resp.content)).convert('RGBA')
                logo = self.add_corners(logo, 100)
        
        qr_img = qr.make_image(image_factory=StyledPilImage,
                        module_drawer=drawer,
                        color_mask=SolidFillColorMask(back_color=bg_color, front_color=main_color),
                        embeded_image=logo)

        inner_eye_mask = self.style_inner_eyes(qr_img)
        outer_eye_mask = self.style_outer_eyes(qr_img)
        intermediate_img = Image.composite(qr_inner_eyes_img, qr_img, inner_eye_mask)
        final_image = Image.composite(qr_outer_eyes_img, intermediate_img, outer_eye_mask)
        img_byte_arr = io.BytesIO()
        final_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr