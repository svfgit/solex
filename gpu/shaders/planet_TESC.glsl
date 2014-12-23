#version 440

// In.
in vec3 verts[];
in vec2 map_uvs[];
in vec2 tex_uvs[];
in int ter_inds[];
in float heights[];

// Out.
layout(vertices = 3) out;
out vec3 tc_verts[];
out vec2 tc_map_uvs[];
out vec2 tc_tex_uvs[];
out int tc_ter_inds[];

// Uniform.
uniform mat4 p3d_ModelViewMatrix;
uniform ivec3 geom_lod[8];
uniform vec2 tess_lod[4];


// Main.
void main()
{
    // Establish distance of triangle from camera.
    float dist_A = length(p3d_ModelViewMatrix*vec4(verts[0],1.0));
    float dist_B = length(p3d_ModelViewMatrix*vec4(verts[1],1.0));
    float dist_C = length(p3d_ModelViewMatrix*vec4(verts[2],1.0));
    float dist = (dist_A+dist_B+dist_C) / 3.0;
    
    // Establish height variation between verts for tess max values. Less
    // height variation means less tesselation is required, even at close
    // distances (i.e. a flat piece of land requires no tesselation at all.)
    float AB_var = abs(heights[0]-heights[1]);
    float BC_var = abs(heights[1]-heights[2]);
    float CA_var = abs(heights[2]-heights[0]);
    int ab_max = 16;
    int bc_max = 16;
    int ca_max = 16;
    for (int j=3; j>=0; j--) {
        float var_thresh = tess_lod[j].x;
        int tess_max = int(tess_lod[j].y);
        if (AB_var < var_thresh) {ab_max = tess_max;}
        if (BC_var < var_thresh) {bc_max = tess_max;}
        if (CA_var < var_thresh) {ca_max = tess_max;}
    }
    // Inner tess is set to avg of outer tess vals to try to
    // minimize artifacts between inner and outer tess levels.
    int in_max = (ab_max+bc_max+ca_max) / 3;
    
    // Find tess levels based on cam dist.
    float tess_AB = 1;
    float tess_BC = 1;
    float tess_CA = 1;
    float tess_inner = 0;
    float thresh;
    
    for (int i=6; i>=0; i--) {
        thresh = geom_lod[i].x;
        if (dist < thresh) {
            tess_inner = min(geom_lod[i].y, in_max);
        }
        if ((dist_A+dist_B)/2 < thresh) {
            tess_AB = min(geom_lod[i].z, ab_max);
        }
        if ((dist_B+dist_C)/2 < thresh) {
            tess_BC = min(geom_lod[i].z, bc_max);
        }
        if ((dist_C+dist_A)/2 < thresh) {
            tess_CA = min(geom_lod[i].z, ca_max);
        }
    }
    
    /* Alternate way to establish geom lod index that avoided looping
    but was no faster in the end. The amount of verts output by the
    TESC shader seems to be the decisive factor in the total shader
    GPU cost, not the amount of work the TESC shader itself does.
    
    int index = max(int(floor(log2(dist)))-7, 0);
    int ab_index = max(int(floor(log2((dist_0+dist_1)/2)))-7, 0);
    int bc_index = max(int(floor(log2((dist_1+dist_2)/2)))-7, 0);
    int ca_index = max(int(floor(log2((dist_2+dist_0)/2)))-7, 0);
    int tess_inner = geom_lod[index].y;
    int tess_AB = geom_lod[ab_index].z;
    int tess_BC = geom_lod[bc_index].z;
    int tess_CA = geom_lod[ca_index].z;*/
    
    // Set tess levels.
    gl_TessLevelInner[0] = tess_inner;
    gl_TessLevelOuter[0] = tess_BC;
    gl_TessLevelOuter[1] = tess_CA;
    gl_TessLevelOuter[2] = tess_AB;
        
    // Map inputs to outputs.
    tc_verts[gl_InvocationID] = verts[gl_InvocationID];
    tc_map_uvs[gl_InvocationID] = map_uvs[gl_InvocationID];
    tc_tex_uvs[gl_InvocationID] = tex_uvs[gl_InvocationID];
    tc_ter_inds[gl_InvocationID] = ter_inds[gl_InvocationID];

}
