#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: B.py
@date: 2025/1/11 13:31
@desc: 
"""
import time
from maya import cmds
from maya.api import OpenMaya as om, OpenMayaAnim as oma
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as splinalg
from scipy.spatial import cKDTree
from logging import getLogger, INFO

logger = getLogger(__name__)
logger.setLevel(INFO)

def timeit( func ):
    def wrapper( *args, **kwargs ):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"Execution time of {func.__name__}: {end_time - start_time} seconds")
        return result

    return wrapper
def as_selection_list( iterable ):
    selection_list = om.MSelectionList()
    if isinstance(iterable, (list, tuple)):
        for item in iterable:
            selection_list.add(item)
    else:
        selection_list.add(iterable)
    return selection_list

def as_dag_path( node ):
    if isinstance(node, om.MDagPath):
        return node
    if isinstance(node, om.MObject):
        return om.MDagPath.getAPathTo(node)
    selection_list = as_selection_list(node)
    return selection_list.getDagPath(0)

def as_depend_node( node ):
    selection_list = as_selection_list(node)
    return om.MFnDependencyNode(selection_list.getDependNode(0))

def as_mfn_mesh( node ):
    dag_path = as_dag_path(node)
    return om.MFnMesh(dag_path)

def as_mfn_skin_cluster( node ):
    dep_node = as_depend_node(node)
    return oma.MFnSkinCluster(dep_node.object())

def load_meshes( source_mesh_name, target_mesh_name ):
    print("Loading meshes...")
    sm = cmds.listRelatives(source_mesh_name, shapes=True)[0] if cmds.objectType(
        source_mesh_name) != "mesh" else source_mesh_name
    tm = cmds.listRelatives(target_mesh_name, shapes=True)[0] if cmds.objectType(
        target_mesh_name) != "mesh" else target_mesh_name
    source_mesh = as_mfn_mesh(sm)
    target_mesh = as_mfn_mesh(tm)
    return source_mesh, target_mesh

@timeit
def get_vertex_positions_as_numpy_array( mesh ):
    points = mesh.getPoints(om.MSpace.kWorld)
    positions = np.array([[point.x, point.y, point.z] for point in points])
    return positions

@timeit
def get_vertex_normals_as_numpy_array( mesh ):
    normals = mesh.getVertexNormals(False, om.MSpace.kWorld)
    normal_array = np.array([[normal.x, normal.y, normal.z] for normal in normals])
    return normal_array

@timeit
def create_vertex_data_array( mesh ):
    vertex_positions = get_vertex_positions_as_numpy_array(mesh)
    vertex_normals = get_vertex_normals_as_numpy_array(mesh)
    num_vertices = mesh.numVertices
    vertex_data = np.zeros(num_vertices,
                           dtype=[("index", np.int64), ("position", np.float64, 3), ("normal", np.float64, 3),
                                  ("face_index", np.int64)])
    vertex_data["index"] = np.arange(num_vertices)
    vertex_data["position"] = vertex_positions
    vertex_data["normal"] = vertex_normals
    vertex_data["face_index"] = -1
    return vertex_data

@timeit
def get_closest_points_by_kdtree( source_mesh, target_vertex_data ):
    source_vertex_data = create_vertex_data_array(source_mesh)
    source_positions = source_vertex_data["position"]
    target_positions = target_vertex_data["position"]
    tree = cKDTree(source_positions)
    distances, indices = tree.query(target_positions)
    nearest_in_source = source_vertex_data[indices]
    nearest_in_source["face_index"] = -1
    return nearest_in_source

@timeit
def filter_high_confidence_matches( target_vertex_data, closest_points_data, max_distance, max_angle ):
    target_positions = target_vertex_data["position"]
    target_normals = target_vertex_data["normal"]
    source_positions = closest_points_data["position"]
    source_normals = closest_points_data["normal"]

    distances = np.linalg.norm(source_positions - target_positions, axis=1)
    cos_angles = np.einsum("ij,ij->i", source_normals, target_normals)
    cos_angles /= (np.linalg.norm(source_normals, axis=1) * np.linalg.norm(target_normals, axis=1))
    cos_angles = np.abs(cos_angles)
    angles = np.arccos(np.clip(cos_angles, -1, 1)) * 180 / np.pi
    high_confidence_indices = np.where((distances <= max_distance) & (angles <= max_angle))[0]
    return high_confidence_indices.tolist()

@timeit
def copy_weights_for_confident_matches( source_mesh, target_mesh, confident_vertex_indices, closest_points_data ):
    source_skin_cluster_name = get_skincluster(source_mesh.name())
    source_skin_cluster = as_mfn_skin_cluster(source_skin_cluster_name)
    deformer_bones = cmds.skinCluster(source_skin_cluster_name, query=True, influence=True)

    target_skin_cluster_name = get_or_create_skincluster(target_mesh.name(), deformer_bones)
    target_skin_cluster = as_mfn_skin_cluster(target_skin_cluster_name)

    known_weights = {}

    num_deformers = len(deformer_bones)

    # Get source weights for all vertices
    source_weights_all, _ = source_skin_cluster.getWeights(source_mesh.dagPath(), om.MObject())
    source_weights_all = np.array(source_weights_all).reshape(-1, num_deformers)

    # Prepare arrays for setting weights
    components_fn = om.MFnSingleIndexedComponent()
    components = components_fn.create(om.MFn.kMeshVertComponent)
    components_fn.addElements(confident_vertex_indices)

    # Map source indices to target indices
    target_indices = confident_vertex_indices
    source_indices = closest_points_data['index'][confident_vertex_indices]

    weights = source_weights_all[source_indices]

    # Flatten weights
    weights_flat = weights.flatten()

    # Set up progress bar
    total_vertices = len(confident_vertex_indices)
    if not cmds.about(batch=True):
        cmds.progressWindow(title='Copying Weights', progress=0, max=total_vertices, status='Copying Weights...',
                            isInterruptable=False)

    # Set weights in chunks to update progress bar
    chunk_size = 1000
    for start in range(0, total_vertices, chunk_size):
        end = min(start + chunk_size, total_vertices)
        current_indices = target_indices[start:end]
        current_weights = weights[start:end].flatten()
        components_chunk_fn = om.MFnSingleIndexedComponent()
        components_chunk = components_chunk_fn.create(om.MFn.kMeshVertComponent)
        components_chunk_fn.addElements(current_indices)
        influence_indices = om.MIntArray(range(num_deformers))
        weights_array = om.MDoubleArray(current_weights.tolist())
        target_skin_cluster.setWeights(target_mesh.dagPath(), components_chunk_fn.object(), influence_indices,
                                       weights_array, False)

        # Update known_weights
        for idx, w in zip(current_indices, weights[start:end]):
            known_weights[idx] = w

        if not cmds.about(batch=True):
            cmds.progressWindow(edit=True, step=end - start)

    if not cmds.about(batch=True):
        cmds.progressWindow(endProgress=True)

    return known_weights

@timeit
def get_skincluster( obj ):
    skin_clusters = cmds.ls(cmds.listHistory(obj), type='skinCluster')
    if skin_clusters:
        return skin_clusters[0]
    else:
        raise RuntimeError("No skinCluster found on object.")

@timeit
def get_or_create_skincluster( obj, deformers ):
    try:
        return get_skincluster(obj)
    except RuntimeError:
        return cmds.skinCluster(deformers, obj, toSelectedBones=True, normalizeWeights=1, name=f"{obj}_skinCluster")[0]

def compute_laplacian_and_mass_matrix( mesh ):
    num_vertices = mesh.numVertices
    L = sp.lil_matrix((num_vertices, num_vertices))
    areas = np.zeros(num_vertices)

    triangle_counts, triangle_vertices = mesh.getTriangles()
    triangles = np.array(triangle_vertices).reshape(-1, 3)

    vertex_positions = get_vertex_positions_as_numpy_array(mesh)
    for tri_indices in triangles:
        tri_positions = vertex_positions[tri_indices]
        add_laplacian_entry_in_place(L, tri_positions, tri_indices)
        add_area_in_place(areas, tri_positions, tri_indices)

    L_csr = L.tocsr()
    M_csr = sp.diags(areas)
    return L_csr, M_csr

def add_laplacian_entry_in_place( L, tri_positions, tri_indices ):
    i1, i2, i3 = tri_indices
    v1, v2, v3 = tri_positions

    cotan1 = compute_cotangent(v2, v1, v3)
    cotan2 = compute_cotangent(v1, v2, v3)
    cotan3 = compute_cotangent(v1, v3, v2)

    for (i, j, cotan) in [(i1, i2, cotan1), (i2, i3, cotan2), (i1, i3, cotan3)]:
        L[i, j] += cotan
        L[j, i] += cotan
        L[i, i] -= cotan
        L[j, j] -= cotan

def add_area_in_place( areas, tri_positions, tri_indices ):
    v1, v2, v3 = tri_positions
    area = 0.5 * np.linalg.norm(np.cross(v2 - v1, v3 - v1))
    for idx in tri_indices:
        areas[idx] += area / 3.0

def compute_cotangent( v1, v2, v3 ):
    a = v2 - v1
    b = v3 - v1
    cos_theta = np.dot(a, b)
    sin_theta = np.linalg.norm(np.cross(a, b))
    cotangent = cos_theta / sin_theta if sin_theta != 0 else 0.0
    return cotangent

def compute_weights_for_remaining_vertices( target_mesh, known_weights ):
    L, M = compute_laplacian_and_mass_matrix(target_mesh)
    Q = -L + L @ sp.diags(1 / M.diagonal()) @ L

    num_vertices = target_mesh.numVertices
    num_bones = len(next(iter(known_weights.values())))
    W = np.zeros((num_vertices, num_bones))

    known_indices = np.array(list(known_weights.keys()))
    unknown_indices = np.array(list(set(range(num_vertices)) - set(known_indices)))

    W[known_indices] = np.array([known_weights[idx] for idx in known_indices])

    Q_UU = Q[unknown_indices][:, unknown_indices]
    Q_UI = Q[unknown_indices][:, known_indices]

    W_I = W[known_indices]
    W_U = np.zeros((len(unknown_indices), num_bones))

    for bone_idx in range(num_bones):
        b = -Q_UI @ W_I[:, bone_idx]
        W_U[:, bone_idx] = splinalg.spsolve(Q_UU, b)

    W[unknown_indices] = W_U
    W = np.clip(W, 0.0, 1.0)
    W_sum = W.sum(axis=1, keepdims=True)
    W_sum[W_sum == 0] = 1
    W /= W_sum

    # Smooth the weights
    W = smooth_weights(target_mesh, W, iterations=2)

    return W

def smooth_weights( mesh, weights, iterations=1 ):
    """Smooth the weights by averaging with neighboring vertices."""
    adjacency_list = build_vertex_adjacency(mesh)
    for _ in range(iterations):
        new_weights = weights.copy()
        for i in range(mesh.numVertices):
            neighbors = adjacency_list[i]
            if neighbors:
                neighbor_weights = weights[neighbors]
                new_weights[i] = (weights[i] + neighbor_weights.mean(axis=0)) / 2
        weights = new_weights
    return weights

def build_vertex_adjacency( mesh ):
    """Build an adjacency list for the mesh vertices."""
    num_vertices = mesh.numVertices
    adjacency = [[] for _ in range(num_vertices)]

    # Create a vertex iterator
    vertex_iter = om.MItMeshVertex(mesh.object())

    while not vertex_iter.isDone():
        idx = vertex_iter.index()
        connected_vertices = vertex_iter.getConnectedVertices()
        adjacency[idx] = connected_vertices
        vertex_iter.next()
    return adjacency

def apply_weight_inpainting( target_mesh, optimized_weights, unconvinced_vertex_indices ):
    target_skin_cluster_name = get_skincluster(target_mesh.name())
    target_skin_cluster = as_mfn_skin_cluster(target_skin_cluster_name)
    num_deformers = optimized_weights.shape[1]

    # Prepare arrays for setting weights
    components_fn = om.MFnSingleIndexedComponent()
    components = components_fn.create(om.MFn.kMeshVertComponent)
    components_fn.addElements(unconvinced_vertex_indices)

    weights = optimized_weights[unconvinced_vertex_indices]

    # Flatten weights
    weights_flat = weights.flatten()

    # Set up progress bar
    total_vertices = len(unconvinced_vertex_indices)
    if not cmds.about(batch=True):
        cmds.progressWindow(title='Applying Inpainted Weights', progress=0, max=total_vertices,
                            status='Applying Weights...', isInterruptable=False)

    # Set weights in chunks to update progress bar
    chunk_size = 1000
    for start in range(0, total_vertices, chunk_size):
        end = min(start + chunk_size, total_vertices)
        current_indices = unconvinced_vertex_indices[start:end]
        current_weights = weights[start:end].flatten()
        components_chunk_fn = om.MFnSingleIndexedComponent()
        components_chunk = components_chunk_fn.create(om.MFn.kMeshVertComponent)
        components_chunk_fn.addElements(current_indices)
        influence_indices = om.MIntArray(range(num_deformers))
        weights_array = om.MDoubleArray(current_weights.tolist())
        target_skin_cluster.setWeights(target_mesh.dagPath(), components_chunk_fn.object(), influence_indices,
                                       weights_array, False)

        if not cmds.about(batch=True):
            cmds.progressWindow(edit=True, step=end - start)

    if not cmds.about(batch=True):
        cmds.progressWindow(endProgress=True)

    print("Done.")

def calculate_threshold_distance( mesh, threadhold_ratio=0.05 ):
    bbox = mesh.boundingBox
    bbox_diag_length = (bbox.max - bbox.min).length()
    return bbox_diag_length * threadhold_ratio

def segregate_vertices_by_confidence( src_mesh, dst_mesh, threshold_distance=0.05, threshold_angle=25.0 ):
    threshold_distance = calculate_threshold_distance(dst_mesh, threshold_distance)
    target_vertex_data = create_vertex_data_array(dst_mesh)
    closest_points_data = get_closest_points_by_kdtree(src_mesh, target_vertex_data)
    confident_vertex_indices = filter_high_confidence_matches(target_vertex_data, closest_points_data,
                                                              threshold_distance, threshold_angle)
    unconvinced_vertex_indices = list(set(range(dst_mesh.numVertices)) - set(confident_vertex_indices))
    return confident_vertex_indices, unconvinced_vertex_indices, closest_points_data

def main():
    selected_meshes = cmds.ls(sl=True)
    if len(selected_meshes) < 2:
        cmds.error("Please select source and target meshes.")
    source_mesh, target_mesh = load_meshes(selected_meshes[0], selected_meshes[1])
    confident_vertex_indices, unconvinced_vertex_indices, closest_points_data = segregate_vertices_by_confidence(
        source_mesh, target_mesh)
    known_weights = copy_weights_for_confident_matches(source_mesh, target_mesh, confident_vertex_indices,
                                                       closest_points_data)
    optimized_weights = compute_weights_for_remaining_vertices(target_mesh, known_weights)
    apply_weight_inpainting(target_mesh, optimized_weights, unconvinced_vertex_indices)

if __name__ == "__main__":
    main()
