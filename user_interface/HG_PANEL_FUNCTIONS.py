import bpy #type: ignore
from .. HG_PCOLL import preview_collections

def draw_sub_spoiler(
    layout, sett, prop_name, label) -> tuple[bool, bpy.types.UILayout]:
    """Draws a ciollapsable box, with title and arrow symbol

    Args:
        layout (UILayout): Layout to draw spoiler in
        sett (PropertyGroup): HumGen Props
        prop_name (str): Name of the BoolProperty that opens/closes spoiler
        label (str): Label to display in the ui

    Returns:
        tuple[bool, bpy.types.UILayout]: 
            bool: True means the box will open in the UI
            UILayout: layout.box to draw items inside the openable box
    """
    boxbox = layout.box()
    boxbox.prop(sett, prop_name,
        icon="TRIA_DOWN" if getattr(sett, prop_name) else "TRIA_RIGHT",
        text = label,
        emboss=False,
        toggle=True)
    
    spoiler_open = getattr(sett, prop_name)
    
    return spoiler_open, boxbox


def draw_panel_switch_header(layout, sett):
    """Draws a enum prop that switches between main humgen panel and extras panel

    Args:
        layout (UILayout): header layout to draw the switch in
        sett (PropertyGroup): HumGen props
    """
    row = layout.row()
    row.scale_x   = 1.5
    row.alignment = 'EXPAND'
    row.prop(sett, 'active_ui_tab', expand = True, icon_only = True)


def get_flow(sett, layout, animation = False) -> bpy.types.UILayout:
    """Returns a property split enabled UILayout

    Args:
        sett (PropertyGroup): HumGen props
        layout (UILayout): layout to draw flor in
        animation (bool, optional): show keyframe dot on row. Defaults to False.

    Returns:
        UILayout: flow layout
    """
   
    col_2 =  layout.column(align = True)
    col_2.use_property_split    = True
    col_2.use_property_decorate = animation
    
    flow = col_2.grid_flow(
        row_major=False,
        columns=1,
        even_columns=True,
        even_rows=False,
        align=True
        ) #is this even necessary now property split is used?
    return flow


def in_creation_phase(hg_rig) -> bool:
    """Checks if this human is in creation phase

    Args:
        hg_rig (Object): HumGen human armature

    Returns:
        bool: True if human in creation phase
    """
    return hg_rig.HG.phase in ['body', 'face', 'skin', 'length']


def draw_spoiler_box(self, ui_name) -> tuple[bool, bpy.types.UILayout]:
    """Draws the spoiler box of the main sections (i.e. body, hair, face)

    Args:
        ui_name (str): name of the category to draw spoiler for

    Returns:
        tuple[bool, bpy.types.UILayout]: 
            bool: True if spoiler is open
            box: layout.box to draw the category UI in
    """
    
    #fallback icons for when custom ones don't load
    icon_dict = {
        'body'          : 'COMMUNITY',
        'face'          : 'COMMUNITY',
        'skin'          : 'COMMUNITY',
        'hair'          : 'OUTLINER_OB_HAIR',
        'length'        : 'EMPTY_SINGLE_ARROW',
        'creation_phase': 'COMMUNITY',
        'clothing'      : 'MATCLOTH',
        'footwear'      : 'MATCLOTH',
        'pose'          : 'ARMATURE_DATA',
        'expression'    : 'GHOST_ENABLED',
        'simulation'    : 'NETWORK_DRIVE',
        'compression'   : 'FOLDER_REDIRECT'
        }

    layout = self.layout
    box = layout.box()

    row = box.row(align=True)
    row.scale_y= 2
    row.alignment = 'LEFT'

    label = ui_name.capitalize().replace('_', ' ')
    try:
        hg_icons =  preview_collections["hg_icons"]
        row.operator('hg3d.uitoggle',
                     text = label,
                     icon_value= hg_icons[ui_name].icon_id,
                     emboss = False
                     ).categ = ui_name
    except:
        icon = icon_dict[ui_name]
        row.operator('hg3d.uitoggle',
                     text = label,
                     icon= icon,
                     emboss=False
                     ).categ = ui_name
    
    is_open = True if self.sett.ui_phase == ui_name else False
    return is_open, box


def searchbox(sett, name, layout):
    """draws a searchbox of the given preview collection

    Args:
        sett (PropertyGroup): HumGen props
        name (str): name of the preview collection to search
        layout (UILayout): layout to draw search box in
    """
    row = layout.row(align= True)
    row.prop(sett, 'search_term_{}'.format(name),
             text = '',
             icon = 'VIEWZOOM'
             )
    
    sett_dict = {
        'poses': sett.search_term_poses,
        'outfit': sett.search_term_outfit,
        'footwear': sett.search_term_footwear,
        'expressions': sett.search_term_expressions,
        'patterns': sett.search_term_patterns
        }
    
    if sett_dict[name] != '':
        row.operator('hg3d.clearsearch',
                     text = '',
                     icon = 'X'
                     ).categ = name

