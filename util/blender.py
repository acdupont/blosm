"""
This file is part of blender-osm (OpenStreetMap importer for Blender).
Copyright (C) 2014-2017 Vladimir Elistratov
prokitektura+support@gmail.com

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import bpy, bmesh


def makeActive(obj, context=None):
    if not context:
        context = bpy.context
    obj.select = True
    context.scene.objects.active = obj


def createMeshObject(name, location=(0., 0., 0.), mesh=None):
    if not mesh:
        mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.objects.link(obj)
    return obj


def createEmptyObject(name, location, hide=False, **kwargs):
    obj = bpy.data.objects.new(name, None)
    obj.location = location
    obj.hide = hide
    obj.hide_select = hide
    obj.hide_render = True
    if kwargs:
        for key in kwargs:
            setattr(obj, key, kwargs[key])
    bpy.context.scene.objects.link(obj)
    return obj


def getBmesh(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    return bm


def setBmesh(obj, bm):
    bm.to_mesh(obj.data)
    bm.free()
    

def pointNormalUpward(face):
    if face.normal.z < 0.:
        face.normal_flip()


def createDiffuseMaterial(name, color):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    return material


def loadMeshFromFile(filepath, name):
    """
    Loads a Blender mesh with the given <name> from the .blend file with the given <filepath>
    """
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        # a Python list (not a Python tuple!) must be set to <data_to.meshes>
        data_to.meshes = [name]
    return data_to.meshes[0]


def loadParticlesFromFile(filepath, name):
    """
    Loads Blender particles settings with the given <name> from the .blend file
    with the given <filepath>
    """
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        # a Python list (not a Python tuple!) must be set to <data_to.meshes>
        data_to.particles = [name]
    return data_to.particles[0]


def appendObjectsFromFile(filepath, *names):
    with bpy.data.libraries.load(filepath) as (data_from, data_to):
        # a Python list (not a Python tuple!) must be set to <data_to.object>
        data_to.objects = list(names)
    # append the objects to the Blender scene
    for obj in data_to.objects:
        obj.select = False
        bpy.context.scene.objects.link(obj)
    # return the appended Blender objects
    return data_to.objects


def getMaterialIndexByName(obj, name, filepath):
    """
    Check if Blender material with the <name> is already set for <obj>,
    if not check if the material is available in bpy.data.material
    (if yes, append it to <obj>),
    if not loads the material with the <name> from the .blend with the given <filepath>
    and append it to <obj>.
    """
    if name in obj.data.materials:
        material = obj.data.materials[name]
        # find index of the material
        for materialIndex,m in enumerate(obj.data.materials):
            if material == m:
                break
    elif name in bpy.data.materials:
        materialIndex = len(obj.data.materials)
        obj.data.materials.append( bpy.data.materials[name] )
    else:
        with bpy.data.libraries.load(filepath) as (data_from, data_to):
            data_to.materials = [name]
        material = data_to.materials[0]
        materialIndex = len(obj.data.materials)
        obj.data.materials.append(material)
    return materialIndex


def getModifier(obj, modifierType):
    for m in obj.modifiers:
        if m.type == modifierType:
            break
    else:
        m = None
    return m