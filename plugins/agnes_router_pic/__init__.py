"""Agnes router plugin registration for Hermes Agent — pic variant (image only)."""
from . import schemas, tools


def register(ctx):
    ctx.register_tool(
        name="generate_image_via_pic01",
        toolset="agnes_router_pic",
        schema=schemas.GENERATE_IMAGE_VIA_PIC01,
        handler=tools.generate_image_via_pic01,
    )
