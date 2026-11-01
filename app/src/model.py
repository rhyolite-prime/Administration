import bpy, math, random, os
from mathutils import Vector
from math import sin, cos, pi
from PIL import Image, ImageDraw, ImageFont

ROOT = '/mnt/agents/output/app'
os.makedirs(f'{ROOT}/assets', exist_ok=True)
os.makedirs(f'{ROOT}/renders', exist_ok=True)
os.makedirs(f'{ROOT}/downloads', exist_ok=True)
random.seed(24)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for block in bpy.data.materials:
    bpy.data.materials.remove(block)

# ---------- materials ----------
def linear(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4

def color(hexcode):
    h = hexcode.lstrip('#')
    return tuple(linear(int(h[i:i+2], 16) / 255) for i in (0, 2, 4)) + (1,)

def material(name, hexcode, rough=.5, metal=0, emission=0, transmission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = color(hexcode)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    p.inputs['Transmission Weight'].default_value = transmission
    if emission:
        p.inputs['Emission Color'].default_value = color(hexcode)
        p.inputs['Emission Strength'].default_value = emission
    return m

M = {
    'magenta': material('Rhyolite magenta • powder-coated aluminum', '8D075C', .28, .35),
    'magenta_dark': material('Deep magenta reveals', '4B1039', .36, .25),
    'white': material('Warm white architectural concrete', 'E8E4DF', .72),
    'stone': material('Pale limestone cladding', 'C9C4BA', .8),
    'dark': material('Charcoal service monolith', '24252A', .42, .25),
    'metal': material('Brushed aluminum', 'A8B0B5', .26, .8),
    'louver': material('Graphite aluminum louvers', '3E484F', .3, .75),
    'glass': material('Blue reflective insulated glazing', '28546C', .16, .42, transmission=.18),
    'glass_dark': material('Smoked glazing', '142C39', .12, .35, transmission=.12),
    'warm_glass': material('Warm occupied interior glazing', '7C674C', .24, .25, emission=.18),
    'light': material('Warm LED 3000K', 'FFD69A', .28, emission=5),
    'asphalt': material('Fine asphalt', '34383B', .92),
    'paving': material('Forecourt basalt pavers', '777876', .82),
    'curb': material('Light curb stone', 'D7D3C9', .85),
    'lawn': material('Lawn', '496B31', .95),
    'leaf': material('Palm leaf green', '35652D', .8),
    'leaf2': material('Sunlit foliage', '638341', .85),
    'trunk': material('Palm trunk', '756044', .95),
    'wood': material('Warm timber soffit', '805233', .6),
    'soil': material('Planting soil', '30251D', 1),
    'flower': material('Magenta flowers', 'B93177', .7),
    'yellow': material('Warm flowers', 'F0B35A', .7),
    'solar': material('Photovoltaic blue silicon', '173B65', .22, .55),
    'solar_grid': material('Solar cell busbars', '7791AC', .32, .65),
    'rubber': material('Tire rubber', '111214', .82),
    'car': material('Obsidian car paint', '171B23', .2, .75),
    'red': material('Tail lamps', 'C91634', .22, emission=1.8),
}

# ---------- geometry helpers ----------
def assign(obj, mat):
    if mat: obj.data.materials.append(M[mat] if isinstance(mat, str) else mat)
    return obj

def bevel(obj, amount=.06, segments=2):
    if amount:
        mod = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
        mod.width = amount; mod.segments = segments
        mod = obj.modifiers.new('Weighted corner normals', 'WEIGHTED_NORMAL')
    return obj

def box(name, loc, dims, mat, bevel_amt=.035, parent=None, rot=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object; o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if rot: o.rotation_euler = rot
    assign(o, mat); bevel(o, bevel_amt)
    if parent: o.parent = parent
    return o

def cyl(name, loc, radius, depth, mat, vertices=24, parent=None, rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object; o.name = name
    if rot: o.rotation_euler = rot
    assign(o, mat); bevel(o, .025, 2)
    if parent: o.parent = parent
    return o

def sphere(name, loc, scale, mat, parent=None, subdivisions=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1, location=loc)
    o = bpy.context.object; o.name = name; o.scale = scale
    assign(o, mat)
    if parent: o.parent = parent
    return o

def empty(name, loc=(0,0,0)):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o); o.location = loc
    return o

font_regular = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
font_bold = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
font_italic = bpy.data.fonts.load('/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf')

def text(name, body, loc, size, mat='white', font=None, align='CENTER', rot=(pi/2,0,0), parent=None, extrude=.008):
    curve = bpy.data.curves.new(name, 'FONT'); curve.body = body
    curve.font = font or font_bold; curve.align_x = align; curve.align_y = 'CENTER'
    curve.size = size; curve.extrude = extrude; curve.bevel_depth = .003
    o = bpy.data.objects.new(name, curve); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot; assign(o, mat)
    if parent: o.parent = parent
    return o

def rod_between(name, a, b, radius, mat, vertices=12, parent=None):
    a, b = Vector(a), Vector(b); d = b-a
    o = cyl(name, (a+b)/2, radius, d.length, mat, vertices, parent)
    o.rotation_euler = d.to_track_quat('Z','Y').to_euler()
    return o

def area_light(name, loc, energy, size, rgb=(1,.78,.52), target=(0,0,0)):
    data = bpy.data.lights.new(name, 'AREA'); data.energy = energy; data.shape = 'DISK'; data.size = size; data.color = rgb
    o = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o

# ---------- site and civil works ----------
box('Infinite ground', (0,0,-.6), (320,320,1), 'lawn', 0)
box('District access road', (0,-31,-.04), (150,15,.18), 'asphalt', .02)
for x in range(-70, 71, 8):
    box('Road center dash', (x,-31,.065), (4,.13,.018), 'white', 0)
box('Site raised platform', (0,2,-.05), (68,50,.35), 'curb', .12)
box('Vehicular forecourt', (-4,-8,.16), (55,29,.16), 'paving', .06)
box('Right garden lawn', (25,5,.23), (14,34,.18), 'lawn', .08)
box('Left parking asphalt', (-25,-3,.25), (11,28,.12), 'asphalt', .04)
box('Front pedestrian walk', (0,-20,.3), (66,3,.2), 'stone', .04)
# parking bays and wheel stops
for y in (-11,-5,1,7):
    for x in (-29.8,-20.2):
        box('Parking stall end line', (x,y,.325), (.10,5.0,.018), 'white', 0)
for y in (-13.5,-8,-2,4,9.5):
    box('Parking stall divider', (-25,y,.325), (10,.10,.018), 'white', 0)
for y in (-10.5,-4.5,1.5,7.5):
    box('Parking wheel stop', (-27.8,y,.48), (.25,2.1,.25), 'curb', .04)
# road curb with black/white blocks
for i in range(44):
    x = -33 + i*1.53
    box('Painted curb block', (x,-22.15,.28), (1.53,.38,.34), 'white' if i%2 else 'dark', .025)
# entrance walkway and steps
box('Entrance pedestrian axis', (1,-11,.38), (13,15,.18), 'stone', .03)
for i in range(4):
    box('Entrance broad step', (1,-5.8-i*.55,.42+i*.12), (12+i*.45,1.1,.22), 'white', .025)

# ---------- primary building massing ----------
for z in (.55,4.65,8.75,12.85):
    box('Continuous structural floor plate', (0,6,z), (40,22,.35), 'white', .05)
box('Rear insulated wall', (0,16.85,6.7), (40,.3,12.4), 'stone', .03)
box('West insulated wall', (-19.85,6,6.7), (.3,22,12.4), 'stone', .03)
box('East insulated wall', (19.85,6,6.7), (.3,22,12.4), 'white', .03)
box('West façade stone pier', (-19.1,-4.85,6.7), (1.5,.45,12.4), 'stone', .03)
box('East façade stone pier', (19.2,-4.85,6.7), (1.4,.45,12.4), 'white', .03)
# central glass curtain wall
for row in range(3):
    z = 2.55 + row*4.1
    for col in range(6):
        x = -8.2 + col*3.15
        box('Atrium insulated glass panel', (x,-5.04,z), (3.02,.16,3.75), 'glass' if (row+col)%4 else 'warm_glass', .025)
    box('Atrium horizontal transom', (-.3,-5.18,z+2.0), (19.2,.18,.12), 'metal', .015)
for col in range(7):
    x = -9.75 + col*3.15
    box('Atrium vertical mullion', (x,-5.2,6.65), (.11,.2,12.1), 'metal', .012)
# left vertical window strips and fins
for col in range(5):
    x = -18.2 + col*1.5
    box('West façade glazing strip', (x,-5.02,6.7), (1.18,.14,10.8), 'glass_dark', .02)
for col in range(7):
    x = -19 + col*1.45
    box('West façade vertical fin', (x,-5.35,6.7), (.14,.65,11.7), 'louver', .018)
# right curtain wall behind brise soleil
for row in range(3):
    for col in range(4):
        box('East façade glazing', (9.2+col*2.55,-5.04,2.55+row*4.1), (2.42,.14,3.75), 'glass', .02)
for i in range(31):
    z = .95 + i*.39
    box('Horizontal solar-shading louver', (13.6,-5.62,z), (11.0,.62,.115), 'louver', .018)
for x in (8.2,11.8,15.4,19.0):
    box('Louver vertical carrier', (x,-5.55,6.7), (.13,.35,12), 'metal', .012)
# side and rear windows
for side in (-1,1):
    for row in range(3):
        for j in range(6):
            y = -2.6+j*3.45
            box('Side elevation window', (side*20.02,y,2.55+row*4.1), (.12,2.5,2.25), 'glass_dark', .02)
            box('Side window head', (side*20.10,y,3.78+row*4.1), (.15,2.7,.10), 'metal', .01)
# interior floor silhouettes and warm light strips
for z in (4.35,8.45,12.55):
    for x in (-7,-2,3,8):
        box('Interior linear luminaire', (x,-3.9,z), (2.6,.18,.07), 'light', .015)
for z in (1.0,5.1,9.2):
    box('Atrium interior floor shadow', (0,-1.8,z), (17,5,.25), 'dark', .02)

# ---------- signature magenta tower and service wall ----------
box('Signature tower shadow reveal', (-4.5,-5.65,11.65), (8.8,2.6,8.3), 'magenta_dark', .09)
box('Signature magenta brand tower', (-4.5,-6.05,11.9), (8.25,2.1,7.9), 'magenta', .08)
text('Main R symbol', 'R', (-4.5,-7.13,14.25), 3.25, font=font_italic, extrude=.035)
text('Main company name', 'RhyolitePrime', (-4.5,-7.14,11.6), .93, font=font_bold, extrude=.018)
text('Main company tagline', 'we innovate...  you grow', (-4.5,-7.15,10.55), .35, font=font_regular, extrude=.01)
box('Service directory monolith', (-14.3,-5.48,6.0), (6.1,.5,9.8), 'dark', .04)
services = [
    ('Cloud Solutions', '& ERP'),
    ('Digital Banking', '& Fintech'),
    ('USSD &', 'Mobile Services'),
    ('AgriTech', '& E-Agriculture'),
    ('IT Consulting', '& Software'),
]
for i,(a,b) in enumerate(services):
    z = 9.35-i*1.72
    # minimalist line icons: cloud, bank, code, agri, globe represented by emblems
    cyl('Service icon medallion', (-16.25,-5.78,z), .28, .05, 'white', 24, rot=(pi/2,0,0))
    text('Service icon glyph', str(i+1), (-16.25,-5.825,z), .26, 'dark', font_bold, extrude=.003)
    text('Service directory line 1', a, (-15.55,-5.78,z+.18), .33, 'white', font_regular, 'LEFT', extrude=.004)
    text('Service directory line 2', b, (-15.55,-5.78,z-.25), .30, 'white', font_regular, 'LEFT', extrude=.004)
# side brand pylon
box('East magenta brand blade', (20.08,3.2,8.4), (.5,7.0,8.0), 'magenta', .05)
text('East R symbol', 'R', (20.36,2.0,10.2), 2.1, font=font_italic, rot=(pi/2,0,pi/2), extrude=.025)

# ---------- entrance canopy, doors and columns ----------
box('Entrance canopy dark reveal', (1.1,-8.25,4.55), (18.2,7.8,.38), 'magenta_dark', .06)
box('Floating entrance canopy', (1.1,-8.35,4.82), (18.6,8.0,.42), 'white', .08)
box('Canopy timber soffit', (1.1,-8.3,4.56), (16.8,6.9,.10), 'wood', .02)
for x in (-5.6,7.8):
    for y in (-10.7,-6.2):
        cyl('Canopy aluminum column', (x,y,2.55), .25, 4.25, 'metal', 32)
        cyl('Column stone base', (x,y,.57), .39, .45, 'stone', 32)
for x in (-5.2,-2.6,0,2.6,5.2):
    box('Entry door glazing', (x,-5.38,2.45), (2.4,.12,3.6), 'glass_dark', .02)
    box('Entry door center stile', (x+1.22,-5.49,2.45), (.07,.10,3.65), 'metal', .01)
    rod_between('Door pull handle', (x+.55,-5.58,1.9), (x+.55,-5.58,2.7), .025, 'metal')
for x in (-5,-1,3,7):
    cyl('Soffit downlight', (x,-8.5,4.48), .11, .04, 'light', 20)

# ---------- roof terrace and photovoltaic array ----------
for x in (-19.4,19.4):
    box('Roof parapet side', (x,6,13.35), (.3,22,1.0), 'white', .03)
box('Roof parapet rear', (0,16.8,13.35), (39,.3,1.0), 'white', .03)
box('Roof parapet front west', (-14,-4.8,13.35), (11,.3,1.0), 'magenta', .03)
box('Roof parapet front east', (14,-4.8,13.35), (11,.3,1.0), 'white', .03)
for x in (-13,-4,5,14):
    for y in (2.0,5.4,8.8,12.2):
        for dx in (-1.25,1.25):
            panel = box('Rooftop photovoltaic module', (x+dx,y,13.65+(y-2)*.025), (2.3,2.8,.10), 'solar', .025, rot=(math.radians(7),0,0))
            for gy in (-.9,0,.9):
                box('PV cell horizontal busbar', (x+dx,y+gy,13.72+(y-2)*.025), (2.2,.022,.015), 'solar_grid', 0, rot=(math.radians(7),0,0))
            for gx in (-.72,0,.72):
                box('PV cell vertical busbar', (x+dx+gx,y,13.72+(y-2)*.025), (.022,2.65,.015), 'solar_grid', 0, rot=(math.radians(7),0,0))
box('Roof service enclosure', (-16,13.5,14.0), (4.5,4.5,1.7), 'stone', .05)
cyl('Roof water tank', (-16,13.5,15.3), 1.0, 1.5, 'metal', 32)

# ---------- monument sign, fence, gate and guardhouse ----------
box('Brand monument wall', (-19.2,-18.2,1.85), (17.2,.65,3.2), 'stone', .12)
box('Monument wall coping', (-19.2,-18.2,3.5), (17.5,.82,.18), 'white', .05)
text('Monument R symbol', 'R', (-25.2,-18.56,2.1), 2.35, 'magenta', font_italic, extrude=.05)
text('Monument company name', 'RhyolitePrime', (-17.8,-18.57,2.25), 1.12, 'dark', font_bold, extrude=.025)
text('Monument tagline', 'we innovate...  you grow', (-17.8,-18.57,1.35), .46, 'magenta', font_regular, extrude=.012)
box('Monument planting bed', (-19.2,-19.2,.48), (18.0,1.7,.45), 'soil', .18)
# fence families
for start,end in ((-32,4.5),(15.5,32)):
    for x in [start+i*.62 for i in range(int((end-start)/.62)+1)]:
        box('Perimeter fence vertical bar', (x,-20.7,1.35), (.075,.09,2.05), 'dark', .012)
    for z in (.55,2.15):
        box('Perimeter fence rail', ((start+end)/2,-20.7,z), (end-start,.12,.10), 'dark', .012)
for x in (-32,-27,-10,4.5,15.5,26,32):
    box('Fence pier', (x,-20.7,1.35), (.5,.5,2.5), 'stone', .04)
    box('Fence pier cap', (x,-20.7,2.65), (.64,.64,.14), 'white', .03)
# animated sliding gate
gate = empty('ANIM • sliding entrance gate')
for x in [5.0+i*.58 for i in range(19)]:
    box('Sliding gate vertical', (x,-20.65,1.4), (.08,.12,2.25), 'dark', .012, gate)
for z in (.35,1.35,2.5):
    box('Sliding gate rail', (10.2,-20.65,z), (10.6,.15,.12), 'dark', .015, gate)
for f,dx in ((1,0),(24,0),(62,10.2),(192,10.2)):
    gate.location.x = dx; gate.keyframe_insert('location', frame=f)
# guardhouse
box('Guardhouse plinth', (23,-15.8,.55), (8,7,.55), 'stone', .08)
box('Guardhouse rear wall', (23,-13,2.25), (7.5,.25,3.4), 'white', .04)
box('Guardhouse east wall', (26.6,-16,2.25), (.25,6,3.4), 'white', .04)
box('Guardhouse west wall', (19.4,-16,2.25), (.25,6,3.4), 'white', .04)
box('Guardhouse front glazing', (23,-18.85,2.3), (6.9,.12,2.7), 'glass_dark', .025)
for x in (20.2,23,25.8):
    box('Guardhouse window mullion', (x,-18.95,2.3), (.09,.12,2.8), 'metal', .012)
box('Guardhouse floating roof', (23,-16,4.25), (8.6,7.3,.35), 'white', .06)
box('Guardhouse magenta fascia', (23,-19.45,4.22), (8.6,.25,.55), 'magenta', .03)
text('Guardhouse label', 'SECURITY', (23,-19.6,4.22), .36, 'white', font_bold, extrude=.008)
# animated boom barrier
boom = empty('ANIM • security barrier', (17.2,-18.8,1.25))
box('Barrier striped arm', (-2.7,0,0), (5.4,.16,.18), 'white', .025, boom)
for x in (-4.8,-3.6,-2.4,-1.2,0):
    box('Barrier red stripe', (x,-.09,0), (.55,.025,.19), 'red', .005, boom)
box('Barrier motor cabinet', (17.2,-18.8,.85), (.65,.65,1.5), 'magenta', .06)
for f,a in ((1,0),(30,0),(66,math.radians(68)),(150,math.radians(68)),(192,math.radians(68))):
    boom.rotation_euler.y = a; boom.keyframe_insert('rotation_euler', frame=f)

# ---------- flags with deforming branded fabric ----------
def make_flag_texture(idx, label):
    path = f'{ROOT}/assets/flag_{idx}.png'
    im = Image.new('RGB', (512,1024), (137,6,86))
    d = ImageDraw.Draw(im)
    bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf', 220)
    reg = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 44)
    d.text((256,280), 'R', font=bold, fill='white', anchor='mm')
    words = label.split(' ')
    y = 630
    for word in words:
        d.text((256,y), word, font=reg, fill='white', anchor='mm'); y += 62
    d.rectangle((18,18,494,1006), outline=(185,55,137), width=4)
    im.save(path)
    m = bpy.data.materials.new(f'Branded woven banner {idx}'); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF'); p.inputs['Roughness'].default_value = .72
    tex = m.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = bpy.data.images.load(path)
    m.node_tree.links.new(tex.outputs['Color'], p.inputs['Base Color'])
    return m

flag_labels = ['Innovative Solutions','Digital Transformation','Financial Inclusion','Agricultural Productivity']
for idx,(x,label) in enumerate(zip((10.5,14,17.5,21),flag_labels)):
    y = -12.4
    cyl('Flagpole', (x-.95,y,3.9), .055, 7.5, 'metal', 16)
    cyl('Flagpole finial', (x-.95,y,7.72), .11, .14, 'metal', 16)
    rod_between('Banner crossbar', (x-.98,y,7.25), (x+.98,y,7.25), .035, 'metal')
    nx,nz = 14,22; verts=[]; faces=[]
    for j in range(nz+1):
        v=j/nz
        for i in range(nx+1):
            u=i/nx
            verts.append((x-.88+1.76*u,y,7.18-4.25*v))
    for j in range(nz):
        for i in range(nx):
            a=j*(nx+1)+i; faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh=bpy.data.meshes.new('Banner fabric grid'); mesh.from_pydata(verts,[],faces); mesh.update()
    o=bpy.data.objects.new('ANIM • branded banner '+str(idx+1),mesh); bpy.context.collection.objects.link(o)
    mesh.materials.append(make_flag_texture(idx,label))
    uv=mesh.uv_layers.new(name='Banner UV')
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index; j,i=divmod(vi,nx+1)
            uv.data[li].uv=(i/nx,1-j/nz)
    o.shape_key_add(name='Basis')
    for k,phase in enumerate((0,pi/2)):
        key=o.shape_key_add(name=f'Breeze {k+1}')
        for vi,v in enumerate(key.data):
            row,col=divmod(vi,nx+1); u=col/nx; vv=row/nz
            v.co.y += (.12+.22*vv)*sin(u*2.5*pi+phase)*(0.25+.75*vv)
            v.co.x += .06*sin(vv*pi+phase)*u
        for f in range(1,194,12):
            key.value = .5+.5*sin((f-1)/48*2*pi+idx*.65+phase)
            key.keyframe_insert('value',frame=f)
    solid=o.modifiers.new('Fabric thickness','SOLIDIFY'); solid.thickness=.012
    sub=o.modifiers.new('Fabric smoothing','SUBSURF'); sub.levels=1

# ---------- procedural landscaping ----------
def palm(x,y,h,seed):
    rng=random.Random(seed)
    leanx=rng.uniform(-.35,.35); leany=rng.uniform(-.25,.25)
    pts=[]
    for i in range(8):
        t=i/7; pts.append((x+leanx*t*t,y+leany*t*t,.35+h*t))
    for i in range(7):
        rod_between('Palm trunk segment',pts[i],pts[i+1],.19-i*.012,'trunk',10)
        if i<6:
            cyl('Palm trunk ring',pts[i+1],.205-i*.012,.07,'trunk',12)
    crown=Vector(pts[-1])
    for k in range(11):
        a=2*pi*k/11+rng.uniform(-.12,.12); length=rng.uniform(2.1,3.1)
        verts=[]; faces=[]
        for j in range(7):
            t=j/6; radial=length*t
            center=crown+Vector((cos(a)*radial,sin(a)*radial,.55*sin(t*pi)-1.15*t*t))
            width=.38*sin(pi*t)**.7+.02
            side=Vector((-sin(a)*width,cos(a)*width,0))
            verts.extend([tuple(center-side),tuple(center+Vector((0,0,.06))),tuple(center+side)])
        for j in range(6):
            b=j*3; faces.extend([(b,b+3,b+4,b+1),(b+1,b+4,b+5,b+2)])
        me=bpy.data.meshes.new('Palm frond'); me.from_pydata(verts,[],faces); me.update()
        ob=bpy.data.objects.new('Arching palm frond',me); bpy.context.collection.objects.link(ob); assign(ob,'leaf' if k%3 else 'leaf2')
        sol=ob.modifiers.new('Frond thickness','SOLIDIFY'); sol.thickness=.015

palm_positions=[(-30,-15,6.5),(-27,13,7),(-22,14,6.2),(24,-7,7),(28,-4,6.3),(25,12,7.4),(29,16,6.8),(-7,-14,5.6),(7,-15,5.8),(14,16,6.4),(4,18,6.5),(-29,7,6.0)]
for i,(x,y,h) in enumerate(palm_positions): palm(x,y,h,100+i)

def broadleaf(x,y,s,seed):
    rng=random.Random(seed)
    cyl('Landscape tree trunk',(x,y,1.6*s),.18*s,3.2*s,'trunk',12)
    for i in range(5):
        a=2*pi*i/5; loc=(x+cos(a)*.8*s,y+sin(a)*.8*s,(3.4+rng.random()*.7)*s)
        sphere('Broadleaf canopy',loc,(1.5*s,1.35*s,1.55*s),'leaf' if i%2 else 'leaf2',subdivisions=2)
for i,(x,y,s) in enumerate([(-34,18,1.3),(-30,24,1.4),(-20,25,1.2),(-5,25,1.1),(11,25,1.25),(30,24,1.4),(33,8,1.15),(33,-8,1.1),(-34,-4,1.0)]):
    broadleaf(x,y,s,300+i)
# clipped hedges, flowers and groundcover
for i in range(35):
    x=-29+i*1.65
    sphere('Front hedge', (x,-18.95,.72), (.75,.52,.55), 'leaf' if i%2 else 'leaf2',subdivisions=2)
for i in range(40):
    x=-27.4+i*.43; y=-19.45+random.uniform(-.3,.3)
    sphere('Monument flowering shrub',(x,y,.68),(.38,.36,.38),'leaf',subdivisions=1)
    for j in range(2):
        sphere('Flower bloom',(x+random.uniform(-.2,.2),y+random.uniform(-.2,.2),.98+random.uniform(0,.14)),(.09,.09,.08),'flower' if i%3 else 'yellow',subdivisions=1)
for x,y in [(24,4),(26,9),(23,16),(-23,11),(-15,-14),(8,-14)]:
    box('Raised landscape bed',(x,y,.45),(4.0,3.2,.45),'soil',.18)
    for i in range(8):
        sphere('Bed shrub',(x+random.uniform(-1.6,1.6),y+random.uniform(-1.2,1.2),.85),(.55,.5,.65),'leaf2' if i%3==0 else 'leaf',subdivisions=2)
# bollard lighting
for x,y in [(-7,-15),(-3,-15),(5,-15),(9,-15),(-27,-17),(16,-17),(27,-17),(24,2),(24,10)]:
    cyl('Landscape bollard',(x,y,.75),.10,1.15,'dark',16)
    cyl('Bollard luminous cap',(x,y,1.3),.13,.16,'light',16)

# ---------- vehicles and human scale ----------
def sedan(name,loc,paint='car',angle=0,animated=False):
    root=empty(name,loc); root.rotation_euler.z=angle
    box(name+' lower body',(0,0,.78),(1.95,4.55,.68),paint,.22,root)
    box(name+' hood',(0,1.45,1.1),(1.82,1.4,.22),paint,.15,root)
    box(name+' trunk',(0,-1.65,1.08),(1.82,1.05,.25),paint,.12,root)
    # trapezoidal glazed cabin
    verts=[(-.83,-1.05,1.05),(.83,-1.05,1.05),(.83,1.0,1.05),(-.83,1.0,1.05),(-.68,-.7,1.75),(.68,-.7,1.75),(.68,.55,1.75),(-.68,.55,1.75)]
    faces=[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    me=bpy.data.meshes.new(name+' cabin mesh'); me.from_pydata(verts,[],faces); me.update()
    ob=bpy.data.objects.new(name+' glazed cabin',me); bpy.context.collection.objects.link(ob); ob.parent=root; assign(ob,'glass_dark'); bevel(ob,.06)
    box(name+' roof',(0,-.08,1.76),(1.42,1.32,.10),paint,.07,root)
    for x in (-.96,.96):
        for y in (-1.45,1.45):
            cyl(name+' tire',(x,y,.55),.39,.25,'rubber',24,root,rot=(0,pi/2,0))
            cyl(name+' alloy wheel',(x*1.02,y,.55),.25,.27,'metal',16,root,rot=(0,pi/2,0))
    for x in (-.64,.64):
        box(name+' headlamp',(x,2.29,.93),(.48,.06,.18),'light',.04,root)
        box(name+' tail lamp',(x,-2.29,.93),(.48,.06,.18),'red',.04,root)
    box(name+' front grille',(0,2.31,.66),(.8,.06,.22),'dark',.03,root)
    return root
hero_car=sedan('ANIM • arriving executive sedan',(9,-35,.08))
for f,y in ((1,-35),(30,-33),(72,-24),(130,-13.5),(192,-11.5)):
    hero_car.location.y=y; hero_car.keyframe_insert('location',frame=f)
for i,(x,y,paint) in enumerate([(-25,-10,'white'),(-25,-4,'car'),(-25,2,'magenta'),(-25,8,'metal'),(29,7,'car')]):
    sedan('Parked sedan '+str(i+1),(x,y,.32),paint,0 if x<0 else pi)

def person(x,y,angle=0):
    root=empty('Visitor',(x,y,.38)); root.rotation_euler.z=angle
    cyl('Visitor torso',(0,0,1.15),.22,.8,'dark',16,root)
    sphere('Visitor head',(0,0,1.78),(.18,.18,.21),'stone',root,2)
    for xx in (-.11,.11): rod_between('Visitor leg',(xx,0,.15),(xx,0,.82),.075,'dark',10,root)
    for xx in (-.28,.28): rod_between('Visitor arm',(xx,0,.85),(xx*.7,0,1.4),.06,'stone',10,root)
person(1,-7); person(3,-8,.3); person(22,-18,-.4)

# ---------- lighting, camera and animation ----------
world=bpy.data.worlds.new('Blue-hour architectural sky'); bpy.context.scene.world=world; world.use_nodes=True
bg=world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(.20,.29,.43,1); bg.inputs['Strength'].default_value=.42
sun_data=bpy.data.lights.new('Late afternoon sun','SUN'); sun_data.energy=2.1; sun_data.angle=.12; sun_data.color=(1.0,.78,.58)
sun=bpy.data.objects.new('Late afternoon sun',sun_data); bpy.context.collection.objects.link(sun); sun.rotation_euler=(math.radians(28),math.radians(-24),math.radians(-32))
area_light('Large sky fill',(-15,-20,28),2400,22,(.58,.72,1.0),(0,0,5))
area_light('Entrance warm bounce',(1,-7,6.0),850,8,(1.0,.63,.34),(1,-5,1))
area_light('Monument wash',(-19,-21,3.5),350,8,(1.0,.72,.43),(-19,-18,1.5))
area_light('Guardhouse wash',(23,-20,5),180,5,(1.0,.76,.5),(23,-17,2))
# camera tour with an animated look target
target=empty('ANIM • camera look target',(0,-1,6))
cam_data=bpy.data.cameras.new('Architectural tour lens'); cam=bpy.data.objects.new('ANIM • exterior approach camera',cam_data); bpy.context.collection.objects.link(cam)
cam_data.lens=39; cam_data.sensor_width=36; cam_data.clip_end=500; cam_data.clip_start=.1
con=cam.constraints.new('TRACK_TO'); con.target=target; con.track_axis='TRACK_NEGATIVE_Z'; con.up_axis='UP_Y'
scene=bpy.context.scene; scene.camera=cam
keys=[
    (1,(-52,-62,34),(0,1,6.2),30),
    (55,(-40,-58,28),(-1,-1,6.4),30),
    (112,(16,-60,26),(1,-2,6.2),30),
    (192,(48,-46,24),(4,-2,6.1),30),
]
for f,loc,targ,lens in keys:
    cam.location=loc; cam.keyframe_insert('location',frame=f)
    target.location=targ; target.keyframe_insert('location',frame=f)
    cam_data.lens=lens; cam_data.keyframe_insert('lens',frame=f)
# Smooth, restrained motion
for ob in (cam,target,hero_car,gate,boom):
    if ob.animation_data and ob.animation_data.action:
        try:
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation='BEZIER'; kp.handle_left_type='AUTO_CLAMPED'; kp.handle_right_type='AUTO_CLAMPED'
        except AttributeError:
            pass
scene.frame_start=1; scene.frame_end=192; scene.render.fps=24
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=32
scene.cycles.use_denoising=True; scene.cycles.use_adaptive_sampling=True; scene.cycles.adaptive_threshold=.08
scene.render.resolution_x=1600; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.film_transparent=False
scene.render.use_file_extension=True
scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
scene.render.fps=24
scene['Project']='RhyolitePrime Headquarters — reference-led architectural reconstruction'
scene['Animation']='8-second exterior approach; moving sedan, sliding gate, rising barrier and breeze-deformed branded flags'
scene['Reference images']='head-quaters.png and head-quaters-full-view.png supplied by user'
scene['Units']='metres'
scene.unit_settings.system='METRIC'
scene.frame_set(96)
# Pack image textures and fonts for a reopenable native source
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=f'{ROOT}/downloads/RhyolitePrime_Headquarters.blend')
scene.render.filepath=f'{ROOT}/renders/RhyolitePrime_Hero.png'
bpy.ops.render.render(write_still=True)
print('MODEL_COMPLETE', len(bpy.data.objects), 'objects')
