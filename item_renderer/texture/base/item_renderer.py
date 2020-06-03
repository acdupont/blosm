import os
import bpy
from util.blender_extra.material import createMaterialFromTemplate, setImage


_claddingMaterialTemplateFilename = "building_material_templates.blend"
_claddingMaterialTemplateName = "tiles_color"


class ItemRendererMixin:
    """
    A mixin class
    """
    
    def getCladdingMaterialId(self, item, claddingTextureInfo):
        return claddingTextureInfo["name"]

    def createCladdingMaterial(self, materialName, claddingTextureInfo):
        materialTemplate = self.getMaterialTemplate(
            _claddingMaterialTemplateFilename,
            _claddingMaterialTemplateName
        )
        if not materialName in bpy.data.materials:
            nodes = createMaterialFromTemplate(materialTemplate, materialName)
            # The wall material (i.e. background) texture,
            # set it just in case
            setImage(
                claddingTextureInfo["name"],
                os.path.join(self.r.assetsDir, claddingTextureInfo["path"]),
                nodes,
                "Cladding Texture"
            )
        # return True for consistency with <self.getFacadeMaterialId(..)>
        return True
    
    def setVertexColor(self, item, face):
        color = item.getCladdingColor()
        if color:
            self.r.setVertexColor(face, color, self.r.layer.vertexColorLayerNameCladding)
    
    def getCladdingTextureInfo(self, item, building):
        return self._getCladdingTextureInfo(item, building)