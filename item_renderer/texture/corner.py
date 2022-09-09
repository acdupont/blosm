from math import cos, radians
from operator import itemgetter
from bisect import bisect_left

from util.blender import linkCollectionFromFile
from ..util import getFilepath


class Corner:
    
    def processCollection(self, item, assetInfo, indices):
        """
        Returns:
            <None> if the corner is visited for the first time or there is something wrong
            A Blender object for the corner with an angle that fits best to the corner in question
        """
        
        # a quick validity check
        if not item.cornerL and not item.cornerR:
            return
        
        cornerL = item.cornerL

        return self.processCorner(
            item,
            assetInfo,
            cornerL,
            # <cornerVert> is a vert at the bottom of the corner item and on its right side
            item.building.renderInfo.verts[indices[1]] \
                if cornerL else\
                # <cornerVert> is a vert at the bottom of the corner item and on its right side
                item.building.renderInfo.verts[indices[0]]
        )
    
    def processCorner(self, item, assetInfo, cornerL, cornerVert):
        """
        Returns:
            <None> if the corner is visited for the first time or there is something wrong
            A Blender object for the corner with an angle that fits best to the corner in question
        """
        facade = item.facade
        
        if cornerL:
            if not facade.cornerInfoL:
                facade.cornerInfoL = facade.vector.prev.facade.cornerInfoR = {}
            cornerInfo = facade.cornerInfoL
        else:
            if not facade.cornerInfoR:
                facade.cornerInfoR = facade.vector.next.facade.cornerInfoL = {}
            cornerInfo = facade.cornerInfoR
        
        # Create a key as a z-coordinate of the bottom of <item>. Note that strings as keys
        # for Python dictionaries and sets work faster than floats
        cornerKey = str( round(cornerVert[2], 3) )
        
        if not cornerKey in cornerInfo:
            # The corner was not visited before. We'll store the corner item and
            # the bottom coordinate of the corner element that belong to <item.facade>
            cornerInfo[cornerKey] = (item, cornerVert)
            # <cornerVert> will be used when we encounter the neighbor part of the corner.
            # it's needed to position the corner asset correctly.
            return
        
        cornerInfo = cornerInfo[cornerKey]
        
        # The styling for the whole corner is defined in either <item> or
        # its item <cornerInfo[0]> on the neighbor side of the corner. We check,
        # which one of them has more style attributes.
        # If the item <cornerInfo[0]> on the neighbor side of the corner has more style
        # attributes, than those style attributes are set for <item>.
        if len(cornerInfo[0].styleBlock.attrs) > len(item.styleBlock.attrs):
            item.styleBlock.attrs = cornerInfo[0].styleBlock.attrs
        
        collectionName = assetInfo["collection"]
        # path to a Blender file defined in <assetInfo>
        filepath = getFilepath(self.r, assetInfo)
        collectionKey = filepath + "_" + collectionName
        
        if not collectionKey in self.r.blenderCollections:
            collection = linkCollectionFromFile(filepath, collectionName)
            if not collection:
                return
            # The first Python list is for corner with convex angles, the second one is
            # for the corners with concave angles
            collectionInfo = (
                collection,
                [ ( obj, -cos(radians(obj["angle"])) ) for obj in collection.objects if obj["angle"]>0.],
                [ ( obj,  cos(radians(obj["angle"])) ) for obj in collection.objects if obj["angle"]<0.]
            )
            collectionInfo[1].sort(key=itemgetter(1))
            collectionInfo[2].sort(key=itemgetter(1))
            self.r.blenderCollections[collectionKey] = collectionInfo
        
        collectionInfo = self.r.blenderCollections[collectionKey]
        # Find a Blender object in the Blender collection represented by <collectionInfo>
        # that angle is the closest one to the angle of the corner in question
        vector = item.facade.vector if cornerL else item.facade.vector.next
        
        if vector.sin > 0.:
            #
            # convex angle of the corner
            #
            _cos = vector.unitVector.dot(vector.prev.unitVector)
            collectionInfo = collectionInfo[1]
        else:
            #
            # concave angle of the corner
            #
            
            # <_cos> is a negated cosine!
            _cos = -vector.unitVector.dot(vector.prev.unitVector)
            collectionInfo = collectionInfo[2]
        
        if not collectionInfo:
            return
        
        i = bisect_left(collectionInfo, _cos, key=itemgetter(1))
        if i==len(collectionInfo) or ( i and (_cos - collectionInfo[i-1][1]) < (collectionInfo[i][1] - _cos) ):
            i -= 1
        obj = collectionInfo[i][0]
        
        # the origin of the corner item
        vertLocation = (cornerInfo[1] + cornerVert)/2.
        item.building.element.l.bmGn.verts.new(vertLocation)
        
        cornerVector = cornerVert-cornerInfo[1] \
            if cornerL else\
            cornerInfo[1] - cornerVert
        
        # Blender object name will be set in <self.prepareGnVerts(..)>,
        # since a separate object may be created later in the code for the given parameters
        # out of the mesh data of <obj>.
        # Vertical scale will be set later in <self.prepareGnVerts(..)>,
        # since we don't have <levelGroup> that is required to set the vertical scale.
        
        # We store <cornerVector>, the horizontal scale and <vertLocation> to avoid
        # their calculation in <self.prepareGnVerts(..)>
        item.building.element.l.attributeValuesGn.append((
            cornerVector,
            cornerVector.length/obj["width"], # horizontal scale
            vertLocation
        ))
        
        return obj
    
    def prepareGnVerts(self, item, levelGroup, indices, assetInfo, obj, numTilesY=1):
        attributeValuesGn = item.building.element.l.attributeValuesGn
        bmVerts = item.building.element.l.bmGn.verts
        
        cornerVector, scaleX, vertLocation = attributeValuesGn[-1]
        # set actual values for <attributeValuesGn[-1]>
        attributeValuesGn[-1] = (
            # set Blender object name
            obj.name,
            cornerVector,
            scaleX,
            # set the vertical scale
            levelGroup.levelHeight/assetInfo["tileHeightM"]
        )
        
        if numTilesY > 1:
            for _ in range(numTilesY-1):
                vertLocation = vertLocation.copy()
                vertLocation[2] += levelGroup.levelHeight
                bmVerts.new(vertLocation)
                attributeValuesGn.append(
                    attributeValuesGn[-1]
                )