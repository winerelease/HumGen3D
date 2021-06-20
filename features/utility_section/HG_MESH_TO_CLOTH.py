from pathlib import Path
import bpy #type: ignore
from ... features.common.HG_COMMON_FUNC import get_prefs, show_message
from ... core.HG_SHAPEKEY_CALCULATOR import (
    build_distance_dict,
    deform_obj_from_difference)
from ... features.finalize_phase.HG_CLOTHING_LOAD import set_cloth_corrective_drivers

class MESH_TO_CLOTH_TOOLS():
    def invoke(self, context, event):
        self.sett= context.scene.HG3D
        self.hg_rig = self.sett.mtc_armature
        
        if not self.hg_rig:
            show_message(self, 'No armature selected in the field above')
            return {'CANCELLED'}
        return self.execute(context)
            
#TODO make compatible with non-standard poses
class HG_OT_AUTOWEIGHT(bpy.types.Operator, MESH_TO_CLOTH_TOOLS):
    bl_idname      = "hg3d.autoweight"
    bl_label       = "Auto weight paint"
    bl_description = "Automatic weight painting"
    bl_options     = {"UNDO"}

    def execute(self,context):     
        cloth_obj = context.object
        for obj in context.selected_objects:
            if obj != cloth_obj:
                obj.select_set(False)
        
        for mod in self.hg_rig.HG.body_obj.modifiers:
            if mod.type == 'MASK':
                mod.show_viewport = False
                mod.show_render   = False
        
        if self.sett.mtc_add_armature_mod:
            armature = next((mod for mod in cloth_obj.modifiers if mod.type == 'ARMATURE'), None) 
            if not armature:
                cloth_obj.modifiers.new(name = 'Cloth Armature', type = 'ARMATURE')
            armature.object = self.hg_rig
            if (2, 90, 0) > bpy.app.version: #use old method for versions older than 2.90
                while cloth_obj.modifiers.find(armature.name) != 0:
                    bpy.ops.object.modifier_move_up({'object': cloth_obj}, modifier=armature.name)
            else:
                bpy.ops.object.modifier_move_to_index(modifier=armature.name, index=0)

        if self.sett.mtc_parent:
            cloth_obj.parent = self.hg_rig

        context.view_layer.objects.active = self.hg_rig.HG.body_obj
        self.hg_rig.select_set(True)
            
        bpy.ops.object.data_transfer(data_type='VGROUP_WEIGHTS', vert_mapping='NEAREST', layers_select_src='ALL', layers_select_dst='NAME', mix_mode='REPLACE')
        bpy.ops.object.data_transfer(layers_select_src='ACTIVE', layers_select_dst='ACTIVE', mix_mode='REPLACE', mix_factor=1.0)
        bone_names = [b.name for b in self.hg_rig.pose.bones]
        for vg in [vg for vg in cloth_obj.vertex_groups if vg.name not in bone_names and not vg.name.startswith('mask')]:
            cloth_obj.vertex_groups.remove(vg)
        
        self.hg_rig.select_set(False)
        context.view_layer.objects.active = cloth_obj

        for mod in self.hg_rig.HG.body_obj.modifiers:
            if mod.type == 'MASK':
                mod.show_viewport = True
                mod.show_render = True

        return {'FINISHED'}

class HG_OT_ADDCORRECTIVE(bpy.types.Operator):
    bl_idname      = "hg3d.addcorrective"
    bl_label       = "Add corrective shapekeys"
    bl_description = "Automatic weight painting"
    bl_options     = {"UNDO"}

    def execute(self,context):   
        self.sett = context.scene.HG3D
        hg_rig    = self.sett.mtc_armature
        sett      = self.sett
        cloth_obj = context.object
        
        body_copy      = hg_rig.HG.body_obj.copy()
        body_copy.data = body_copy.data.copy()
        context.collection.objects.link(body_copy)
        
        if not context.object or context.object.type != 'MESH':
            show_message(self, 'Active object is not a mesh')
            return {'FINISHED'}
        
        remove_list = [driver for driver in body_copy.data.shape_keys.animation_data.drivers]
        for driver in remove_list:
            body_copy.data.shape_keys.animation_data.drivers.remove(driver)
        
        distance_dict = build_distance_dict(body_copy, cloth_obj, apply = False) 
        
        if cloth_obj.data.shape_keys:
            for sk in [sk for sk in cloth_obj.data.shape_keys.key_blocks if sk.name.startswith('cor')]:
                cloth_obj.shape_key_remove(sk)
        
        if not cloth_obj.data.shape_keys:
            sk = cloth_obj.shape_key_add(name = 'Basis')
            sk.interpolation = 'KEY_LINEAR'
        
        shapekey_list = self._build_cor_shapkey_list(sett)
        
        sks = body_copy.data.shape_keys.key_blocks
        for sk in sks:
            if sk.name.startswith('cor'):
                sk.value = 0
            
        for sk in shapekey_list:
            sks[sk].value = 1
            deform_obj_from_difference(sk, distance_dict, body_copy, cloth_obj, as_shapekey=True)
            sks[sk].value = 0
        
        set_cloth_corrective_drivers(hg_rig.HG.body_obj, cloth_obj.data.shape_keys.key_blocks)
        
        bpy.data.objects.remove(body_copy)
        cloth_obj.select_set(True)
        return {'FINISHED'}

    def _build_cor_shapkey_list(self, sett) -> list:
        shapekey_list = []
        if sett.shapekey_calc_type == 'pants':
            shapekey_list.extend(['cor_LegFrontRaise_Rt',
                                  'cor_LegFrontRaise_Lt',
                                  'cor_FootDown_Lt',
                                  'cor_FootDown_Rt'])
        elif sett.shapekey_calc_type == 'top':
            shapekey_list.extend(['cor_ElbowBend_Lt',
                                  'cor_ElbowBend_Rt',
                                  'cor_ShoulderSideRaise_Lt',
                                  'cor_ShoulderSideRaise_Rt',
                                  'cor_ShoulderFrontRaise_Lt',
                                  'cor_ShoulderFrontRaise_Rt'])
        elif sett.shapekey_calc_type == 'shoe':
            shapekey_list.extend(['cor_FootDown_Lt',
                                  'cor_FootDown_Rt'])
        else:
            shapekey_list.extend(['cor_ElbowBend_Lt',
                                  'cor_ElbowBend_Rt',
                                  'cor_ShoulderSideRaise_Lt',
                                  'cor_ShoulderSideRaise_Rt',
                                  'cor_ShoulderFrontRaise_Lt',
                                  'cor_ShoulderFrontRaise_Rt',
                                  'cor_LegFrontRaise_Rt',
                                  'cor_LegFrontRaise_Lt',
                                  'cor_FootDown_Lt',
                                  'cor_FootDown_Rt'])
                                  
        return shapekey_list
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text = 'Adding shapekeys for type: {}'.format(
            context.scene.HG3D.shapekey_calc_type.capitalize())
                     )
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class HG_OT_ADDCLOTHMATH(bpy.types.Operator, MESH_TO_CLOTH_TOOLS):
    bl_idname      = "hg3d.addclothmat"
    bl_label       = "Add clothing material"
    bl_description = "Adds the default HumGen clothing material for you to set up"
    bl_options     = {"UNDO"}

    def execute(self,context): 
        pref = get_prefs()
        mat_file = pref.filepath + str(Path('/outfits/HG_CLOTHING_MAT.blend'))
        
        with bpy.data.libraries.load(mat_file, link = False) as (data_from ,data_to):
            data_to.materials = data_from.materials['HG_CLOTHING']
            
        mat = data_to.materials[0]

        ob = context.object
        if ob.data.materials:
            ob.data.materials[0] = mat
        else:
            ob.data.materials.append(mat)
        
        ob['cloth'] = 1
        
        return {'FINISHED'}