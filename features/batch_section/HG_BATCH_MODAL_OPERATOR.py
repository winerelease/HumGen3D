'''
Inactive file to be implemented later, batch mode for generating multiple 
humans at once
'''

import json
import os
import random
import subprocess
import time
from pathlib import Path

import bpy #type:ignore
from ... API import humgen

from ...features.batch_section.HG_BATCH_FUNC import (get_batch_marker_list,
                                                     has_associated_human)
from ...features.batch_section.HG_QUICK_GENERATOR import toggle_hair_visibility
from ...user_interface.HG_BATCH_UILIST import uilist_refresh
from ..common.HG_COMMON_FUNC import get_prefs, hg_delete, show_message
from ..creation_phase.HG_CREATION import (HG_CREATION_BASE,
                                          set_eevee_ao_and_strip)

def status_text_callback(header, context):  
    sett   = context.scene.HG3D
    layout = header.layout

    layout.separator_spacer()
    layout.alignment = 'EXPAND'
    
    row = layout.row(align=False)
    row.alignment = 'CENTER'
    
    layout.label(text=f'Building Human {sett.batch_idx}', icon='TIME')
    
    col         = layout.column()
    col.scale_x = 1.6
    col.prop(sett, "batch_progress")

    layout.label(text='Press ESC to cancel', icon='EVENT_ESC')
    
    layout.separator_spacer()
    
class HG_BATCH_GENERATE(bpy.types.Operator, HG_CREATION_BASE):
    """
    clears searchfield INACTIVE
    """
    bl_idname = "hg3d.generate"
    bl_label = "Generate"
    bl_description = "Generates specified amount of humans"
    bl_options = {"REGISTER", "UNDO"}

    run_immediately: bpy.props.BoolProperty(default = False)

    def __init__(self):
        self.human_idx = 0
        self.generate_queue = get_batch_marker_list(bpy.context)
        self.finish_modal = False
        self.timer = None
        self.start_time = time.time()

    def invoke(self, context, event):
        sett = context.scene.HG3D
        
        markers_with_associated_human = list(filter(has_associated_human, self.generate_queue))
          
        if self.run_immediately or not markers_with_associated_human:
            self._initiate_modal(context, sett)
            set_eevee_ao_and_strip(context)
            
            return {'RUNNING_MODAL'}
        else:
            self._show_dialog_to_confirm_deleting_humans(context)
            return {'CANCELLED'}

    def _initiate_modal(self, context, sett):
        wm = context.window_manager
        wm.modal_handler_add(self)

        sett.batch_progress = 0

        self.human_idx = 0
        self.timer = wm.event_timer_add(0.01, window=context.window)

        sett.batch_idx = 1
        context.workspace.status_text_set(status_text_callback)

    def _show_dialog_to_confirm_deleting_humans(self, context):
        generate_queue = self.generate_queue
            
        def draw(self, context):
            layout = self.layout
                
            nonlocal generate_queue
                
            i = 0
            for marker in filter(has_associated_human, generate_queue):
                layout.label(text = marker['associated_human'].name)
                i += 1
                    
                if i > 9:
                    layout.label(text = f'+ {len(generate_queue) - 10} more')
                    break
                    
            layout.separator()
                
            layout.operator_context = 'INVOKE_DEFAULT'    
            layout.operator("hg3d.generate", text="Generate anyway").run_immediately = True
            return 

        context.window_manager.popup_menu(draw, title="This will delete these humans:")

    def modal(self, context, event):
        """ Event handling. """
        
        sett = context.scene.HG3D      

        if self.finish_modal:
            context.area.tag_redraw()
            context.workspace.status_text_set(text=None)

            sett.batch_idx = 0
            
            print('ENDING TIME: ', time.time()-self.start_time)
            return {'FINISHED'}
        
        elif event.type in ['ESC']:
            self._cancel(sett, context)
            
            return {'RUNNING_MODAL'}
        
        elif event.type == 'TIMER':
            #Check if all humans in the list are already generated
            if self.human_idx == len(self.generate_queue):   
                self.finish_modal = True
                return {'RUNNING_MODAL'}
            
            current_marker = self.generate_queue[self.human_idx]
            if has_associated_human(current_marker):
                self._delete_old_associated_human(current_marker)
                
            pose_type = current_marker['hg_batch_marker']
            settings_dict = self._build_settings_dict(context, sett, pose_type)    
            result = humgen.generate_human_in_background(context, settings_dict)
            
            if not result:
                self._cancel(sett, context)
                return {'RUNNING_MODAL'}
            else:
                hg_rig = result
            
            hg_rig.location = current_marker.location
            hg_rig.rotation_euler = current_marker.rotation_euler
            current_marker['associated_human'] = hg_rig
            
            self.human_idx += 1
            
            if self.human_idx > 0:
                progress = self.human_idx / (len(self.generate_queue))
                sett.batch_progress =  int(progress * 100)
                 
            sett.batch_idx += 1
            context.workspace.status_text_set(status_text_callback)
         
            return {'RUNNING_MODAL'}
        
        else:
            return {'RUNNING_MODAL'}

    def _delete_old_associated_human(self, marker):
        associated_human = marker['associated_human']
        for child in associated_human.children[:]:
            hg_delete(child)
        hg_delete(associated_human)

    def _cancel(self, sett, context):
        print('modal is cancelling')
        sett.batch_progress = sett.batch_progress + (100 - sett.batch_progress) / 2.0

        print('finishing because escape')
        self.finish_modal = True
        context.workspace.status_text_set(status_text_callback)
        return {'CANCELLED'}

    def _build_settings_dict(self, context, sett, pose_type) -> dict:
        sd = {}
        
        for quality_setting in self._get_quality_setting_names():
            sd[quality_setting] = getattr(sett, f'batch_{quality_setting}')
        
        sd['gender'] = str(random.choices(
            ('male', 'female'),
            weights = (sett.male_chance, sett.female_chance),
            k=1)[0])
        
        sd['ethnicity'] = str(random.choices(
            ('caucasian', 'black', 'asian'),
            weights = (
                sett.caucasian_chance,
                sett.black_chance,
                sett.asian_chance
                ),
            k=1
            )[0])
                                    
        sd['add_hair'] = sett.batch_hair
        sd['hair_type'] = sett.batch_hairtype
        sd['hair_quality'] = getattr(sett, f'batch_hair_quality_{sett.batch_hairtype}')
        
        sd['add_expression'] = sett.batch_expression
        if sett.batch_expression:
            self._add_category_list(context, sd, 'expressions') 
        
        sd['add_clothing'] = sett.batch_clothing
        
        self._add_category_list(context, sd, 'clothing') 
        
        sd['pose_type'] = pose_type
        
        return sd

    def _add_category_list(self, context, sd, pcoll_name):
        
        #TODO fix naming inconsistency
        label = 'expressions' if pcoll_name == 'expressions' else 'clothing'
        
        enabled_categories = [
                i.library_name
                for i in getattr(context.scene, f'batch_{label}_col')
                if i.enabled]
        if not enabled_categories:
            uilist_refresh(self, context, label)
            enabled_categories = getattr(context.scene, [i.library_name for i in f'batch_{label}_col'])
            
        sd[f'{pcoll_name}_category'] = random.choice(enabled_categories)

    def _get_quality_setting_names(self):
        return [
            'delete_backup',
            'apply_shapekeys',
            'apply_armature_modifier',
            'remove_clothing_subdiv',
            'remove_clothing_solidify',
            'apply_clothing_geometry_masks',
            'texture_resolution',
            'poly_reduction',
            'apply_poly_reduction'
        ]
        