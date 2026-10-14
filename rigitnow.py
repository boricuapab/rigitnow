"""Full-body FK character rig builder for Maya."""
import json
import os
from functools import wraps
from maya import cmds, mel
import maya.api.OpenMaya as om
import math
import shutil

ROOT = 'rigitnow_rig'
PREFIX = 'rn_'

def transaction(fn):
    @wraps(fn)
    def run(*args, **kwargs):
        cmds.undoInfo(openChunk=True, chunkName=fn.__name__)
        failed = False
        try:
            return fn(*args, **kwargs)
        except Exception:
            failed = True
            raise
        finally:
            cmds.undoInfo(closeChunk=True)
            if failed and cmds.undoInfo(q=True,undoName=True) == fn.__name__:
                cmds.undo()
    return run

def template():
    with open(os.path.join(os.path.dirname(__file__), 'reference_template.json')) as stream:
        return json.load(stream)

def joint(name):
    return PREFIX + name

def editable():
    if not cmds.objExists(ROOT):
        raise RuntimeError('Create the skeleton first.')
    if cmds.objExists('rn_controls_grp') or cmds.ls('rn_*', type='skinCluster'):
        raise RuntimeError('Joint placement and orientation must finish before controls or skinning.')

def meshes(selection=None):
    selection = selection if selection is not None else cmds.ls(sl=True, long=True)
    result = set()
    for node in selection:
        if cmds.nodeType(node) == 'mesh':
            node = cmds.listRelatives(node, parent=True, fullPath=True)[0]
        for transform in [node] + (cmds.listRelatives(node, ad=True, type='transform', fullPath=True) or []):
            if cmds.listRelatives(transform, shapes=True, noIntermediate=True, type='mesh'):
                result.add(transform)
    return sorted(result)

@transaction
def create_skeleton(geometry=None, positions=None):
    if cmds.objExists(ROOT):
        raise RuntimeError('A rigitnow rig already exists in this scene.')
    geometry = meshes(geometry)
    if not geometry:
        raise RuntimeError('Select the character geometry or its group.')
    bounds = cmds.exactWorldBoundingBox(geometry)
    height = bounds[4] - bounds[1]
    scale = height / 16.30337635
    width_scale = (bounds[3]-bounds[0]) / 20.2816
    # Median mesh center avoids a large cape shifting the skeleton behind the body.
    centers_z = sorted((cmds.exactWorldBoundingBox(m)[2]+cmds.exactWorldBoundingBox(m)[5])/2 for m in geometry)
    center_z = centers_z[len(centers_z)//2]
    data = template()['joints']
    cmds.group(empty=True, name=ROOT)
    cmds.sets(geometry,name='rn_character_geometry')
    cmds.addAttr(ROOT, ln='rigitnowVersion', dt='string')
    cmds.setAttr(ROOT+'.rigitnowVersion', '1.0.0', type='string')
    cmds.addAttr(ROOT, ln='templateScale', at='double', dv=scale)
    cmds.group(empty=True, name='rn_joints_grp', parent=ROOT)
    remaining = dict(data)
    while remaining:
        for name, spec in list(remaining.items()):
            parent = spec['parent']
            if parent and parent in remaining:
                continue
            cmds.select(clear=True)
            p = positions.get(name) if positions and name in positions else [spec['position'][0]*width_scale+(bounds[0]+bounds[3])/2, spec['position'][1]*scale+bounds[1], spec['position'][2]*scale+center_z]
            j = cmds.joint(name=joint(name), p=p, radius=height/180)
            cmds.parent(j, joint(parent) if parent else 'rn_joints_grp')
            cmds.setAttr(j+'.displayLocalAxis', True)
            del remaining[name]
    cmds.select(joint('Root'))
    if not positions:
        mirror('X','L')
    orient_reference()
    return [joint(n) for n in data]

@transaction
def mirror(axis='X', source='L'):
    editable()
    axis = axis.upper()
    if axis not in 'XYZ' or len(axis) != 1 or source not in ('L','R'):
        raise ValueError('Choose X, Y or Z and L or R.')
    target = 'R' if source == 'L' else 'L'
    data = template()['joints']
    positions = {n:cmds.xform(joint(n), q=True, ws=True, t=True) for n in data}
    updates = {}
    for n, p in positions.items():
        if source in n and n.replace(source,target) in data:
            p = list(p)
            p['XYZ'.index(axis)] *= -1
            updates[n.replace(source,target)] = p
    # Parents before children, then restore every unaffected world position.
    positions.update(updates)
    for n in sorted(data, key=lambda n: len(cmds.ls(joint(n), long=True)[0].split('|'))):
        cmds.xform(joint(n), ws=True, t=positions[n])
    return list(updates)

@transaction
def orient(axis='X', up='Y', scope='All', world_up=None):
    editable()
    axis, up = axis.lower(), up.lower()
    world_up = (world_up or up).lower()
    if axis not in ('x','y','z') or up not in ('x','y','z') or axis == up:
        raise ValueError('Aim and up axes must be different.')
    data = template()['joints']
    preserved_positions = {n:cmds.xform(joint(n),q=True,ws=True,t=True) for n in data}
    if scope == 'Arms and fingers':
        data = {n:v for n,v in data.items() if n.startswith(('Shoulder','Humerus','Forearm','Hand','Thumb','Index','Middle','Ring','Pinky'))}
    elif scope == 'Legs, spine and neck':
        data = {n:v for n,v in data.items() if not n.startswith(('Shoulder','Humerus','Forearm','Hand','Thumb','Index','Middle','Ring','Pinky'))}
    order = axis + up + next(a for a in 'xyz' if a not in (axis,up))
    for n in sorted(data, key=lambda n: len(cmds.ls(joint(n), long=True)[0].split('|'))):
        j = joint(n)
        children = cmds.listRelatives(j, children=True, type='joint', fullPath=True) or []
        if children:
            # Explicit primary child prevents branch ordering from aiming the pelvis at a leg.
            primary = {'Root':'Chest', 'Chest':'Neck', 'Neck':'Head', 'HandL':'MiddleL1', 'HandR':'MiddleR1'}.get(n)
            aim_child = joint(primary) if primary else children[0]
            detached = []
            for child in children:
                detached.append(cmds.parent(child,world=True)[0])
            cmds.setAttr(j+'.rotate',0,0,0)
            primary_name=aim_child.split('|')[-1]
            cmds.parent(primary_name,j)
            cmds.joint(j,edit=True,orientJoint=order,secondaryAxisOrient=world_up+'up',zeroScaleOrient=True)
            for child in detached:
                if child.split('|')[-1] != primary_name:
                    cmds.parent(child,j)
        else:
            cmds.setAttr(j+'.jointOrient',0,0,0)
            cmds.setAttr(j+'.rotate',0,0,0)
    for n in sorted(preserved_positions,key=lambda n:len(cmds.ls(joint(n),long=True)[0].split('|'))):
        cmds.xform(joint(n),ws=True,t=preserved_positions[n])
    return order

def orient_reference():
    orient('X','Y','Arms and fingers','Y')
    orient('X','Y','Legs, spine and neck','Z')

@transaction
def create_controls():
    editable()
    data = template()
    scale = cmds.getAttr(ROOT+'.templateScale')
    cmds.group(empty=True,name='rn_controls_grp',parent=ROOT)
    controls, offsets = {}, {}
    for name,spec in data['controls'].items():
        flat = spec['points']
        points = [[v*scale for v in flat[i:i+3]] for i in range(0,len(flat),3)]
        if not spec['joint']:
            closed_points=points+[points[0]]
            c=cmds.curve(name=PREFIX+name,degree=1,p=closed_points,periodic=True,knot=list(range(len(closed_points))))
        else:
            c = cmds.curve(name=PREFIX+name, degree=spec['degree'], p=points)
            cmds.closeCurve(c,constructionHistory=False,preserveShape=True,replaceOriginal=True)
        offset = cmds.group(empty=True,name=c+'_offset')
        cmds.parent(c,offset,relative=True)
        cmds.parent(offset,'rn_controls_grp')
        for s in cmds.listRelatives(c,shapes=True):
            cmds.setAttr(s+'.overrideEnabled',True)
            cmds.setAttr(s+'.overrideColor',spec['color'])
        if spec['joint']:
            n = spec['joint'][0]
            cmds.matchTransform(offset,joint(n),pos=True,rot=True)
            controls[n], offsets[n] = c, offset
        else:
            global_ctrl = c
    for n,c in controls.items():
        parent = data['joints'][n]['parent']
        cmds.parent(offsets[n],controls.get(parent,global_ctrl))
        cmds.parentConstraint(c,joint(n),mo=True,name=c+'_parentConstraint')
        # Global scale is inherited once from rn_joints_grp. Per-joint scale
        # constraints conflict with joint segment scale compensation.
        cmds.setAttr(joint(n)+'.displayLocalAxis',False)
        for attr in ('sx','sy','sz','v'):
            cmds.setAttr(c+'.'+attr,lock=True,keyable=False)
        if n != 'Root':
            for attr in ('tx','ty','tz'):
                cmds.setAttr(c+'.'+attr,lock=True,keyable=False)
    cmds.parentConstraint(global_ctrl,'rn_joints_grp',mo=True)
    cmds.scaleConstraint(global_ctrl,'rn_joints_grp',mo=True)
    cmds.sets(list(controls.values())+[global_ctrl],name='rn_animation_controls')
    fit_control_shapes()
    cmds.select(global_ctrl)
    return list(controls.values())+[global_ctrl]

@transaction
def repair_global_scaling():
    """Remove redundant joint scale drivers from an existing rigitnow rig."""
    removed=[]
    for n in template()['joints']:
        j=joint(n)
        if not cmds.objExists(j): continue
        drivers=set()
        for axis in 'XYZ':
            drivers.update(cmds.listConnections(j+'.scale'+axis,source=True,destination=False,type='scaleConstraint') or [])
        if drivers:
            cmds.delete(list(drivers))
            removed.extend(drivers)
            cmds.setAttr(j+'.scale',1,1,1)
    return removed

@transaction
def fit_control_shapes():
    """Replace FK shapes with closed rings fitted near each pivot; retain drivers."""
    geometry = meshes(cmds.sets('rn_character_geometry',q=True)) if cmds.objExists('rn_character_geometry') else meshes(cmds.ls(type='mesh',long=True))
    if not geometry:
        raise RuntimeError('No character geometry is available for control fitting.')
    bounds = cmds.exactWorldBoundingBox(geometry)
    height = bounds[4]-bounds[1]
    vertices=[]
    for mesh in geometry:
        flat=cmds.xform(mesh+'.vtx[*]',q=True,ws=True,t=True)
        vertices.extend(om.MVector(*flat[i:i+3]) for i in range(0,len(flat),3))
    for name,spec in template()['controls'].items():
        if not spec['joint']: continue
        c=PREFIX+name
        if not cmds.objExists(c): continue
        j=spec['joint'][0]
        center=om.MVector(*cmds.xform(joint(j),q=True,ws=True,t=True))
        matrix=om.MMatrix(cmds.xform(c,q=True,ws=True,matrix=True))
        if j in ('Root','Chest','Neck','Head'):
            normal=om.MVector(0,1,0)
        else:
            children=cmds.listRelatives(joint(j),children=True,type='joint') or []
            target=joint('Middle'+j[-1]+'1') if j.startswith('Hand') else children[0] if children else None
            normal=(om.MVector(*cmds.xform(target,q=True,ws=True,t=True))-center).normal() if target else om.MVector(1,0,0)*matrix
        local_normal=(normal*matrix.inverse()).normal()
        near=sorted(vertices,key=lambda v:(v-center).length())[:16]
        radial=sorted(math.sqrt(max(0,(v-center).length()**2-((v-center)*normal)**2)) for v in near)
        radius=radial[int((len(radial)-1)*.75)]*1.15
        finger=any(j.startswith(f) for f in ('Thumb','Index','Middle','Ring','Pinky'))
        radius=max(height*.004,min(radius,height*(.012 if finger else .12)))
        temp=cmds.circle(normal=list(local_normal),radius=radius,degree=3,sections=16,constructionHistory=False)[0]
        old=cmds.listRelatives(c,shapes=True,type='nurbsCurve') or []
        shape=cmds.listRelatives(temp,shapes=True)[0]
        cmds.parent(shape,c,shape=True,relative=True)
        cmds.delete(temp)
        if old: cmds.delete(old)
        shape=cmds.listRelatives(c,shapes=True,type='nurbsCurve')[0]
        cmds.setAttr(shape+'.overrideEnabled',True)
        cmds.setAttr(shape+'.overrideColor',spec['color'])
    mirror_controls()
    return True

@transaction
def mirror_controls():
    """Reflect positive-X control origins and CVs while retaining right-side axes."""
    pairs=[]
    data=template()['controls']
    joint_controls={v['joint'][0]:PREFIX+n for n,v in data.items() if v['joint']}
    for j,left in joint_controls.items():
        partner=j.replace('L','R')
        if partner==j or partner not in joint_controls: continue
        if cmds.xform(left,q=True,ws=True,t=True)[0] <= 0: continue
        right=joint_controls[partner]
        p=cmds.xform(left,q=True,ws=True,t=True)
        pairs.append((left,right,[-p[0],p[1],p[2]]))
    for left,right,p in sorted(pairs,key=lambda pair:len(cmds.ls(pair[1],long=True)[0].split('|'))):
        offset=cmds.listRelatives(right,parent=True)[0]
        cmds.xform(offset,ws=True,t=p)
    for left,right,p in pairs:
        left_shape=cmds.listRelatives(left,shapes=True,type='nurbsCurve')[0]
        right_shape=cmds.listRelatives(right,shapes=True,type='nurbsCurve')[0]
        flat=cmds.xform(left_shape+'.cv[*]',q=True,ws=True,t=True)
        inverse=om.MMatrix(cmds.xform(right,q=True,ws=True,matrix=True)).inverse()
        for i in range(0,len(flat),3):
            local=om.MPoint(-flat[i],flat[i+1],flat[i+2])*inverse
            cmds.xform(right_shape+'.cv[%d]'%(i//3),os=True,t=(local.x,local.y,local.z))
    return len(pairs)

@transaction
def skin(geometry=None, max_influences=4):
    if not cmds.objExists(joint('Root')):
        raise RuntimeError('Create the skeleton first.')
    geometry = meshes(geometry)
    if not geometry:
        raise RuntimeError('Select polygon geometry to skin.')
    for mesh in geometry:
        if cmds.ls(cmds.listHistory(mesh),type='skinCluster'):
            raise RuntimeError('Geometry is already skinned: '+mesh)
    influences = [joint(n) for n in template()['joints'] if not n.endswith('_end')]
    return [cmds.skinCluster(influences,m,toSelectedBones=True,bindMethod=0,skinMethod=0,maximumInfluences=max_influences,obeyMaxInfluences=True,normalizeWeights=1,name='rn_'+m.split('|')[-1]+'_skin')[0] for m in geometry]

def show():
    window = 'rigitnow_window'
    if cmds.window(window,exists=True): cmds.deleteUI(window)
    cmds.window(window,title='rigitnow | Full Body FK Rig',widthHeight=(420,720))
    cmds.columnLayout(adjustableColumn=True,rowSpacing=8)
    cmds.text(label='1. Select character geometry, then create joints.\n2. Move joints in the viewport before building controls.',align='left')
    def invoke(fn):
        def callback(*_):
            try: fn()
            except Exception as error: cmds.warning(str(error))
        return callback
    cmds.button(label='Build Rig — T-Pose',height=44,command=invoke(create_skeleton))
    cmds.button(label='Select All Rig Joints',command=invoke(lambda:cmds.select([joint(n) for n in template()['joints']])))
    plane=cmds.optionMenu(label='Mirror plane normal'); [cmds.menuItem(label=a) for a in 'XYZ']
    side=cmds.optionMenu(label='Mirror source'); [cmds.menuItem(label=a) for a in ('L','R')]
    cmds.button(label='Mirror Joints',command=invoke(lambda:mirror(cmds.optionMenu(plane,q=True,value=True),cmds.optionMenu(side,q=True,value=True))))
    aim=cmds.optionMenu(label='Axis down chain'); [cmds.menuItem(label=a) for a in 'XYZ']
    up=cmds.optionMenu(label='Secondary axis'); [cmds.menuItem(label=a) for a in 'XYZ']; cmds.optionMenu(up,e=True,value='Y')
    world=cmds.optionMenu(label='Secondary axis world orientation'); [cmds.menuItem(label=a) for a in 'XYZ']; cmds.optionMenu(world,e=True,value='Y')
    scope=cmds.optionMenu(label='Orientation region'); [cmds.menuItem(label=a) for a in ('Arms and fingers','Legs, spine and neck','All')]
    cmds.button(label='Orient Joint Hierarchy',command=invoke(lambda:orient(cmds.optionMenu(aim,q=True,value=True),cmds.optionMenu(up,q=True,value=True),cmds.optionMenu(scope,q=True,value=True),cmds.optionMenu(world,q=True,value=True))))
    cmds.button(label='Apply Character Orientation Preset',command=invoke(orient_reference))
    cmds.button(label='Add All Animation Controls',command=invoke(create_controls))
    cmds.button(label='Fit Control Shapes to Geometry',command=invoke(fit_control_shapes))
    cmds.button(label='Mirror Controls +X to -X',command=invoke(mirror_controls))
    cmds.text(label='Select character geometry again before binding.',align='left')
    cmds.button(label='Skin Selected Character Geometry',command=invoke(skin))
    cmds.showWindow(window)

def install_shelf():
    icon_name='rigiitnow_icon.png'
    module_dir=os.path.dirname(os.path.abspath(__file__))
    candidates=[os.path.join(module_dir,'icons',icon_name),os.path.join(os.path.dirname(module_dir),'icons',icon_name)]
    source=next((p for p in candidates if os.path.isfile(p)),None)
    icon_dir=cmds.internalVar(userBitmapsDir=True)
    if source:
        os.makedirs(icon_dir,exist_ok=True)
        target=os.path.join(icon_dir,icon_name)
        if os.path.normcase(os.path.abspath(source))!=os.path.normcase(os.path.abspath(target)):
            shutil.copy2(source,target)
    icon=icon_name if os.path.isfile(os.path.join(icon_dir,icon_name)) else 'kinJoint.png'
    shelf = 'rigitnow'
    legacy='rigitnowShelf'
    if cmds.shelfLayout(legacy,exists=True):
        children=cmds.shelfLayout(legacy,q=True,childArray=True) or []
        if all(cmds.shelfButton(child,exists=True) and cmds.shelfButton(child,q=True,label=True)=='rigitnow' for child in children):
            cmds.deleteUI(legacy)
    if not cmds.shelfLayout(shelf,exists=True):
        cmds.shelfLayout(shelf,parent=mel.eval('$tmp=$gShelfTopLevel'))
    for child in cmds.shelfLayout(shelf,q=True,childArray=True) or []:
        if cmds.shelfButton(child,q=True,label=True)=='rigitnow':
            cmds.shelfButton(child,edit=True,image=icon,imageOverlayLabel='')
            mel.eval('saveAllShelves $gShelfTopLevel;')
            return
    cmds.shelfButton(parent=shelf,label='rigitnow',image=icon,annotation='Open rigitnow character rigging tool',sourceType='python',command='import rigitnow; rigitnow.show()')
    mel.eval('saveAllShelves $gShelfTopLevel;')
