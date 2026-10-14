# rigitnow

Full-body FK character rigging plugin for Maya.

## Install

On Windows, run the included batch installer. It installs the plugin, rigging module, template, and shelf icon for the current user and registers the package with Maya. It copies the icon into the shared Maya icons folder and the user icons folders for existing Maya versions. Restart Maya after installation, load **rigitnow_plugin** in Plug-in Manager, and enable **Auto load**.

Keep the included plugin, Python module, and rig template together. In Maya's Plug-in Manager, browse to the included plugin, load it, and enable **Auto load**. Loading creates a **rigitnow** shelf with a tool button. The plugin also registers the MEL command `rigitnow`.

## Workflow

1. Select character polygon meshes or their group. **Build Rig — T-Pose** creates 51 editable full-body joints, fitted approximately to the geometry height and width. The layout includes shoulders, arms, hands, five fingers, legs, feet, torso, neck and head.
2. Reposition joints in the viewport. **Mirror Joints** reflects the chosen side through the world-origin plane whose normal is X, Y or Z. X mirrors across YZ, Y across XZ, Z across XY. Characters should be centered on the chosen plane. **Apply Character Orientation Preset** uses X primary/Y secondary, with world Y up for arms/fingers and world Z up for legs/spine/neck. These presets are also applied when building the skeleton. Custom primary, secondary and world axes can be applied to either region or the whole hierarchy. Branches aim toward the torso/head or middle finger; tips inherit parent orientation.
3. **Add All Animation Controls** builds all 39 controls with left blue/right red/center yellow/global green colors. FK controls are closed circles, sized from nearby character vertices and aligned across their joint chains; pelvis, chest, neck and head rings wrap horizontally. Each control origin sits on its joint. The global control uses a closed custom outline. **Fit Control Shapes to Geometry** refreshes these shapes without changing control connections and mirrors the positive-X shapes to negative X. **Mirror Controls +X to -X** repeats this mirror after shape edits. Controls follow the FK hierarchy; root and global translation are available. Joint editing is blocked once controls or skin exist.
4. Select geometry again. **Skin Selected Character Geometry** binds unskinned meshes with normalized linear skinning and up to four influences. Already-skinned meshes are rejected. Use Maya's Paint Skin Weights for final deformation refinement.

Actions are undo chunks and failed operations roll back. One rig per scene is supported. The rig uses FK and does not include an IK switch, facial system, or automatic cloth simulation. Bounding-box fitting supplies a starting layout; anatomy and pose adjustments remain necessary for unusual proportions and non-T-pose models.

