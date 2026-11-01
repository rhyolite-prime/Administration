import bpy, os
ROOT='/mnt/agents/output/app'
path=f'{ROOT}/downloads/RhyolitePrime_Headquarters.blend'
bpy.ops.wm.open_mainfile(filepath=path)
# glTF does not carry font curves; convert only in this export session.
bpy.ops.object.select_all(action='DESELECT')
fonts=[o for o in bpy.context.scene.objects if o.type=='FONT']
for o in fonts: o.select_set(True)
if fonts:
    bpy.context.view_layer.objects.active=fonts[0]
    bpy.ops.object.convert(target='MESH')
bpy.ops.object.select_all(action='SELECT')
out=f'{ROOT}/downloads/RhyolitePrime_Headquarters_Animated.glb'
bpy.ops.export_scene.gltf(filepath=out,export_format='GLB',export_animations=True,export_frame_range=True,export_force_sampling=True,export_cameras=True,export_lights=False,export_extras=True)
print('GLB_EXPORTED',out,os.path.getsize(out),len(fonts),'text objects converted')
# Reopen the actual deliverable to verify geometry and animation data survive.
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=out)
scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=='MESH']
assert meshes and len(meshes)>100, 'GLB reimport is empty or incomplete'
assert len(bpy.data.actions)>0, 'GLB animation data missing'
print('GLB_REIMPORT_OK',len(meshes),'meshes',len(bpy.data.actions),'actions',len(scene.objects),'objects')
