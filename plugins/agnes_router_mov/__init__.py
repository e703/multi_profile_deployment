"""Agnes router plugin registration for Hermes Agent — mov variant (video only)."""
from . import schemas, tools


def register(ctx):
    ctx.register_tool(
        name="generate_video_via_mov01",
        toolset="agnes_router_mov",
        schema=schemas.GENERATE_VIDEO_VIA_MOV01,
        handler=tools.generate_video_via_mov01,
    )
