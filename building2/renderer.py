import bpy
from renderer import Renderer
from .layer import BuildingLayer
from .item_store import ItemStore
from .texture_exporter import TextureExporter

from item.building import Building
from item.footprint import Footprint
from item.facade import Facade
from item.level import Level
from item.div import Div
from item.bottom import Bottom
from item.window import Window
from item.entrance import Entrance
from item.corner import Corner
from item.balcony import Balcony
from item.chimney import Chimney

from item.roof_flat import RoofFlat
from item.roof_flat_multi import RoofFlatMulti
from item.roof_profile import RoofProfile
from item.roof_generatrix import RoofGeneratrix
from item.roof_hipped import RoofHipped
from item.roof_hipped_multi import RoofHippedMulti
from item.roof_side import RoofSide

_itemClasses = (
        Building,
        Footprint,
        Facade,
        Level,
        Div,
        Bottom,
        Window,
        Entrance,
        Corner,
        Balcony,
        Chimney,
        RoofFlat,
        RoofFlatMulti,
        RoofProfile,
        RoofGeneratrix,
        RoofHipped,
        RoofHippedMulti,
        RoofSide
    )


class BuildingRendererNew(Renderer):
    
    def __init__(self, app, styleStore, itemRenderers, getStyle=None):
        self.app = app
        app.addRenderer(self)
        
        # offset for a Blender object created if <layer.singleObject is False>
        self.offset = None
        
        self.styleStore = styleStore
        
        self.assetsDir = app.assetsDir
        self.assetPackageDir = app.assetPackageDir
        
        # do wee need to apply a cladding color for facade textures?
        self.useCladdingColor = True
        
        self.itemRenderers = itemRenderers
        self.facadeRenderer = itemRenderers["Facade"]
        
        self.exportMaterials = app.enableExperimentalFeatures and app.importForExport
        
        if self.exportMaterials:
            self.textureExporter = TextureExporter(self.assetsDir, self.assetPackageDir)
            # Do we need to cache <claddingTextureInfo> for each cladding material?
            self.cacheCladdingTextureInfo = False
        
        # initialize item renderers
        for item in itemRenderers:
            itemRenderers[item].init(itemRenderers, self)
        
        self.getStyle = getStyle
        self.itemStore = ItemStore(_itemClasses)
        
        self._cache = {}
        
        self.buildingActions = []
        self.footprintActions = []
        # "rev" stands for "render extruded volumes"
        self.revActions = []
    
    def prepare(self):
        if self.app.preferMesh:
            # A key to the dictionary below is an object name as it's defined in <self.app.assetStore>.
            # A related value is tuple that consists of 
            # (1) A link to a Blender object in the file defined in the related asset info.
            # (2) A list of custom attributes defined for this object. The addon will
            # create a separate object for each unique set of the attributes. All those created objects will
            # share the same Blender mesh.
            # (3) A dictionary:
            #     A key is a combination of custom attributes described above.
            #     A value is the name of the Blender object created for the unique set of attributes
            #     used in the key.
            self.meshAssets = {}
            # A Python dictionary to store processed information about Blender objects that belong to
            # a Blender collection. Each collection is defined in the asset store.
            self.blenderCollections = {}
            
            _collectionName = "blosm_building_assets"
            if not _collectionName in bpy.data.collections:
                bpy.data.collections.new(_collectionName)
            # a Blender collection for instances on the points cloud
            self.buildingAssetsCollection = bpy.data.collections[_collectionName]
            
            # check if a Geometry Nodes setup with the name "blosm_gn_building" is already available
            _gnName, _gnCollection = "blosm_gn_building", "Collection Info"
            node_groups = bpy.data.node_groups
            if _gnName in node_groups and _gnCollection in node_groups[_gnName].nodes:
                self.gnBuilding = node_groups[_gnName]
            else:
                # load the Geometry Nodes setup with the name "blosm_gn_building" from <self.app.baseAssetPath>
                with bpy.data.libraries.load(self.app.baseAssetPath) as (_, data_to):
                    data_to.node_groups = [_gnName]
                self.gnBuilding = data_to.node_groups[0]
            # set the input of <self.gnBuilding.nodes[_gnCollection]> to <self.buildingAssetsCollection>
            self.gnBuilding.nodes[_gnCollection].inputs['Collection'].default_value = self.buildingAssetsCollection
        
        if self.app.singleObject:
            for layer in self.app.layers:
                if isinstance(layer, BuildingLayer):
                    layer.obj = self.createBlenderObject(
                        layer.name,
                        layer.location,
                        collection = self.collection,
                        parent = None
                    )
                    layer.prepare()

    def finalize(self):
        if self.app.singleObject:
            for layer in self.app.layers:
                if isinstance(layer, BuildingLayer):
                    layer.finalize(self)
    
    def cleanup(self):
        for action in self.buildingActions:
            action.cleanup()
        
        if self.exportMaterials:
            self.textureExporter.cleanup()
        
        self._cache.clear()
    
    def render(self, building, data):
        parts = building.parts
        itemStore = self.itemStore
        
        #if "id" in outline.tags: print(outline.tags["id"]) #DEBUG OSM id
        
        building.renderInfo = Building(data)
        
        # get the style of the building
        buildingStyle = self.styleStore.get(self.getStyle(building, self.app))
        if not buildingStyle:
            # skip the building
            return
        building.renderInfo.setStyleMeta(buildingStyle)
        
        #if self.app.renderAfterExtrude:
        #    self.preRender(building)
        
        if not parts or building.alsoPart:
            # the building has no parts
            footprint = Footprint(building, building)
            # The attribute <footprint> below may be used in calculation of the area of
            # the building footprint or in <action.terrain.Terrain>
            #building.footprint = footprint
            itemStore.add(footprint)
        if parts:
            itemStore.add((Footprint(part, building) for part in parts), Footprint, len(parts))
        
        for actions in (self.buildingActions, self.footprintActions):
            for action in actions:
                action.do(building, buildingStyle, self)
                if itemStore.skip:
                    break
            if itemStore.skip:
                break
        itemStore.clear()
        
        if itemStore.skip:
            itemStore.skip = False
        elif self.app.renderAfterExtrude:
            self.postRender(building.element)
    
    def renderExtrudedVolumes(self, building, data):
        #self.preRender(building)
        
        if not self.app.singleObject:
            renderInfo = building.renderInfo
            layer = building.element.l
            
            layer.obj = self.createBlenderObject(
                self.getName(building.element),
                renderInfo.offsetBlenderObject,
                collection = layer.getCollection(self.collection),
                parent = layer.getParent( layer.getCollection(self.collection) )
            )
            layer.prepare()
        
        # render building footprint
        if not building.parts or building.alsoPart:
            self.renderExtrudedVolume(building.footprint, True)
        # render building parts
        for part in building.parts:
            self.renderExtrudedVolume(part.footprint, False)
        
        self.postRender(building.element)
    
    def renderExtrudedVolume(self, footprint, isBldgFootprint):
        if not footprint:
            return
        
        if not footprint.noWalls:
            for action in self.revActions:
                action.do(footprint)
            
            self.facadeRenderer.render(footprint)
        
        footprint.roofRenderer.render(footprint.roofItem)
    
    def createFace(self, footprint, indices):
        bm = footprint.building.element.l.bm
        renderInfo = footprint.building.renderInfo
        verts = renderInfo.verts
        bmVerts = renderInfo.bmVerts
        
        # extend <bmVerts> to have the same number of vertices as in <verts>
        bmVerts.extend(None for _ in range(len(verts)-len(bmVerts)))
        
        # check if we have BMVerts for for all <indices>
        for index in indices:
            if not bmVerts[index]:
                bmVerts[index] = bm.verts.new(
                    (verts[index] + renderInfo.offsetVertex) if renderInfo.offsetVertex else verts[index]
                )
        
        return bm.faces.new(bmVerts[index] for index in indices)
    
    def setUvs(self, face, uvs, layer, uvLayerName):
        # assign uv coordinates
        uvLayer = layer.bm.loops.layers.uv[uvLayerName]
        loops = face.loops
        for loop,uv in zip(loops, uvs):
            loop[uvLayer].uv = uv
    
    def setVertexColor(self, face, color, layer, layerName):
        vertexColorLayer = layer.bm.loops.layers.color[layerName]
        for loop in face.loops:
            loop[vertexColorLayer] = color

    def setMaterial(self, layer, face, materialName):
        """
        Set material (actually material index) for the given <face>.
        """
        materialIndices = layer.materialIndices
        materials = layer.obj.data.materials
        
        if not materialName in materialIndices:
            materialIndices[materialName] = len(materials)
            materials.append(bpy.data.materials[materialName] if materialName else None)
        face.material_index = materialIndices[materialName]