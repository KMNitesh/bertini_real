"""
Foong Min Wong
University of Wisconsin, Eau Claire
Fall 2018 - Spring 2019
Implementing raw and smooth stereolithography (STL) surface export feature for Bertini_real

.. module:: tmesh
    :platform: Unix, Windows
    :synopsis: The tmesh uses Trimesh for raw/smooth STL export and normal fixing.

"""
import bertini_real
import copy
import math
import numpy as np
import os
from stl import mesh
import trimesh
from itertools import chain


class ReversableList(list):
    """ Create a ReversableList object for reversing order of data """

    def reverse(self):
        """ A reverse function for raw surface data

        Returns a reversed list
        """
        return list(reversed(self))

class TMesh():
    """ Create a TMesh object for exporting STL files """

    def __init__(self, data=None):
    	
        """ Read data from disk

            Args:
                data: surface decomposition data

        """

        if data is None:
            self.decomposition = bertini_real.data.ReadMostRecent()
        else:
            self.decomposition = data

    def raw(self):
        """ Export raw decomposition of surfaces"""

        print('\n' + '\x1b[0;34;40m' +
              'Generating raw STL surface...' + '\x1b[0m')

        points = extract_points(self)

        surf = self.decomposition.surface

        num_faces = surf.num_faces

        which_faces = list(range(num_faces))

        if not len(which_faces):
            which_faces = list(range(num_faces))

        num_total_faces = 0
        for ii in range(len(which_faces)):
            curr_face = surf.faces[which_faces[ii]]
            num_total_faces = num_total_faces + 2 * \
                (curr_face['num left'] + curr_face['num right'] + 2)
        num_total_faces = num_total_faces * 2

        total_face_index = 0
        TT = []

        for cc in range(len(which_faces)):
            ii = which_faces[cc]
            face = surf.faces[ii]

            if (face['middle slice index']) == -1:
                continue

            case = 1
            left_edge_counter = 0
            right_edge_counter = 0

            T = []

            while 1:
                ## top edge ##
                if case == 1:

                    case += 1
                    if face['top'] < 0:
                        continue

                    curr_edge = -10
                    if(face['system top'] == 'input_critical_curve'):
                        curr_edge = surf.critical_curve.edges[face['top']]
                    elif(face['system top'] == 'input_surf_sphere'):
                        curr_edge = surf.sphere_curve.edges[face['top']]
                    else:
                        for zz in range(len(surf.singular_curves)):
                            if(surf.singular_names[zz] == face['system top']):
                                curr_edge = surf.singular_curves[
                                    zz].edges[face['top']]

                    # print(curr_edge)
                    # print(curr_edge[0],curr_edge[1],curr_edge[2])
                    # print(type(curr_edge))

                    if(curr_edge == -10):
                        continue

                    if (curr_edge[0] < 0 and curr_edge[1] < 0 and curr_edge[2] < 0):
                        continue

                    curr_edge = ReversableList(curr_edge)
                    curr_edge = curr_edge.reverse()

                ## bottom edge ##
                elif case == 2:

                    case += 1

                    if face['bottom'] < 0:
                        continue

                    curr_edge = -10
                    if(face['system bottom'] == 'input_critical_curve'):
                        curr_edge = surf.critical_curve.edges[face['bottom']]
                    elif(face['system bottom'] == 'input_surf_sphere'):
                        curr_edge = surf.sphere_curve.edges[face['bottom']]
                    else:
                        for zz in range(len(surf.singular_curves)):
                            if(surf.singular_names[zz] == face['system bottom']):
                                curr_edge = surf.singular_curves[
                                    zz].edges[face['bottom']]

                    if(curr_edge == -10):
                        continue

                    if (curr_edge[0] < 0 and curr_edge[1] < 0 and curr_edge[2] < 0):
                        continue

                ## left edge ##
                elif case == 3:

                    if left_edge_counter < face['num left']:

                        if face['left'][left_edge_counter] < 0:
                            continue

                        slice_ind = face['middle slice index']
                        edge_ind = face['left'][left_edge_counter]

                        curr_edge = surf.critical_point_slices[
                            slice_ind].edges[edge_ind]
                        left_edge_counter = left_edge_counter + 1  # increment

                    else:
                        case = case + 1
                        continue

                ## right edge ##
                elif case == 4:

                    if right_edge_counter < face['num right']:

                        if face['right'][right_edge_counter] < 0:
                            continue

                        slice_ind = face['middle slice index'] + 1
                        edge_ind = face['right'][right_edge_counter]
                        curr_edge = surf.critical_point_slices[
                            slice_ind].edges[edge_ind]
                        right_edge_counter = right_edge_counter + 1

                        curr_edge = ReversableList(curr_edge)
                        curr_edge = curr_edge.reverse()

                    else:
                        case += 1
                        continue

                ## last case ##
                elif case == 5:
                    break

                t1 = [points[curr_edge[0]], points[curr_edge[1]],
                      points[face['midpoint']]]
                t2 = [points[curr_edge[1]], points[curr_edge[2]],
                      points[face['midpoint']]]

                t3 = (curr_edge[0], curr_edge[1], face['midpoint'])
                t4 = (curr_edge[1], curr_edge[2], face['midpoint'])

                T.append(t1)
                T.append(t2)

                TT.append(t3)
                TT.append(t4)

        faces = [TT]
        vertex = []

        for p in points:
            vertex.append(p)

        vertex_np_array = np.array(vertex)
        face = []

        for f in faces:
            for tri in f:
                face.append([tri[0], tri[1], tri[2]])

        face_np_array = np.array(face)

        raw_mesh = trimesh.Trimesh(vertex_np_array, face_np_array)

        fileName = os.getcwd().split(os.sep)[-1]

        raw_mesh.fix_normals()

        raw_mesh.export(file_obj='raw_' + fileName +
                        '.stl', file_type='stl')

        print("Export " + '\x1b[0;35;40m' + "raw_" +
              fileName + ".stl" + '\x1b[0m' + " successfully")

    def smooth(self):

        print('\n' + '\x1b[0;34;40m' +
              'Generating smooth STL surface...' + '\x1b[0m')

        points = extract_points(self)

        faces = self.decomposition.surface.surface_sampler_data

        vertex = []

        for p in points:
            vertex.append(p)

        vertex_np_array = np.array(vertex)

        face = []

        for f in faces:
            for tri in f:
                face.append([tri[0], tri[1], tri[2]])

        face_np_array = np.array(face)

        smooth_mesh = trimesh.Trimesh(vertex_np_array, face_np_array)

        fileName = os.getcwd().split(os.sep)[-1]

        smooth_mesh.fix_normals()

        smooth_mesh.export(file_obj='smooth_' +
                           fileName + '.stl', file_type='stl')

        print("Export " + '\x1b[0;35;40m' + "smooth_" +
              fileName + ".stl" + '\x1b[0m' + " successfully")

    def solidify(self, totalDist, offset):

        # stl = input('Enter a STL filename:')

        stl = "mystl.stl"

        offset = 0
        total = 0.1

        tmesh = trimesh.load(str(stl))
        A = copy.deepcopy(tmesh)
        B = copy.deepcopy(tmesh)

        # reverse every triangles and flip every normals
        B.invert()

        # calculate A, B vertex normals
        vertexnormsA = A.vertex_normals
        vertexnormsB = B.vertex_normals

        distA = (total) * (offset + 1) / 2
        distB = (total) * (1 - (offset + 1) / 2)

        # print(len(A.vertices))
        # # create a list to store  amount of distance for A to move
        # # amountDistA = []

        # for vnorm in A.vertex_normals:
        #     amountDistA.append(vnorm * distA)

        # # for each vertexA, move vertexA to distA corresponding to vertexnormals of A
        # for v in A.vertices:
        #     v += vnorm[v] * distA

        # create A & B vertices that move corresponding to vertex normals and
        # distance
        A.vertices = [v + vn * distA for v,
                      vn in zip(A.vertices, A.vertex_normals)]
        B.vertices = [v + vn * distB for v,
                      vn in zip(B.vertices, B.vertex_normals)]

        # # create a list to store  amount of distance for B to move
        # amountDistB = []

        # for vnorm in B.vertex_normals:
        #     amountDistB.append(vnorm * distB)

        # # for each vertexA, move vertexB to corresponding B vertex normals
        # for v in B.vertices:
        #     # for each amount of distance B
        #     for i in range(len(amountDistB)):
        #         v += amountDistB[i]

        # # add boundary faces
        # # concatenate, add new faces, not adding new vertices

        ####

        # FIND when it drops the point (two libraries)
        # WHAT POINT IT THROWS AWAY THE DISCONNECTED THE EXTRA POINT
        # 	WHEN YOUT TRIMESH
        # unreferenced vertices

        ####

        faces = self.decomposition.surface

        # print(self.decomposition.)
        # # # indices of this point, bounding sphere
        sphere_curve = faces.sphere_curve.sampler_data  # [[x,x,x],[0],[1]]

        numVerts = len(A.vertices)

        T = []

        f = A.facets_boundary
        ff = [l.tolist() for l in f]
        ff = list(chain.from_iterable(ff))

        # print(sphere_curve)

        print(sphere_curve)
        for edge in sphere_curve:
            # for edge in ff:
                # for i in range(numVerts-1):
            for i in range(len(edge) - 1):
                # t1 = [edge[i],edge[i+1],edge[i]+numVerts]
                # t2 = [edge[i],edge[i]+numVerts,edge[i+1]+numVerts]
                # t1 = [edge[i],edge[i+1],edge[i]+len(edge)]
                # t2 = [edge[i],edge[i]+len(edge),edge[i+1]+len(edge)]

                t1 = [edge[i], edge[i + 1], edge[i] + numVerts]
                t2 = [edge[i + 1], edge[i] + numVerts, edge[i + 1] + numVerts]

                T.append(t1)
                T.append(t2)

#--------------------------------------------------------------------------------------------------------------------------------------------------#
# Export stl
        newA = trimesh.Trimesh(A.vertices, A.faces)

        newA.fix_normals()

        fileName1 = os.getcwd().split(os.sep)[-1]

        newA.export(file_obj='newA_' +
                    fileName1 + '.stl', file_type='stl')

        newB = trimesh.Trimesh(B.vertices, B.faces)

        fileName2 = os.getcwd().split(os.sep)[-1]

        newB.fix_normals()

        newB.export(file_obj='newB_' +
                    fileName2 + '.stl', file_type='stl')

        Q = np.concatenate((newA.vertices, newB.vertices), axis=0)

        newBoundary = trimesh.Trimesh(Q, T)

        newBoundary.fix_normals()

        # newBoundary.fill_holes()

        newBoundary.export(file_obj='newBoundary_' +
                           fileName2 + '.stl', file_type='stl')

        finalmesh = newA + newB + newB

        finalmesh.export(file_obj='final_' +
                         fileName2 + '.stl', file_type='stl')

        #  python3 solidify.py && ~/stlviewer/./stlviewer final_whitney.stl

        # mesh1 = trimesh.load('newA_whitney.stl')

        # mesh2 = trimesh.load('newB_whitney.stl')
        # final = trimesh.load('final_whitney.stl')
        # final.show()
        # mesh1.show()

        # (mesh2).show()

#---------------------------------------------------------------------------#

        # read mostrecent()
        # x.surface.sphere_curve
        # walk down the edge, add the triangles,
        # trimesh add vertices
        # for each edge, then for each consecutive pair
        # https://github.com/mikedh/trimesh/blob/master/trimesh/creation.py

        # Junk: testing some codes
        # create a list to store new vertices B
        # newvB = []
        # # for each vertexA, move vertexB to corresponding B vertex normals
        # for v in B.vertices:
        #     for vnorm in vertexnormsB:
        #         newvB.append(np.add(v,list(np.asarray(vnorm)*distB)))

    # def test(self):
    #     stl = "mystl.stl"
    #     tmesh = trimesh.load(str(stl))
    #     print(tmesh.vertices)
    #     print(tmesh.faces)
    #     nested_lst_of_tuples = [tuple(l) for l in tmesh.faces]
    #     print([nested_lst_of_tuples])


def extract_points(self):
    """ Extract points from vertices """

    points = []

    for v in self.decomposition.vertices:
        q = [None] * 3

        for i in range(3):
            q[i] = v['point'][i].real
        points.append(q)

    return points


def raw(data=None):
    """ Create a TMesh object and export raw surface """

    surface = TMesh(data)
    surface.raw()


def smooth(data=None):
    """ Create a TMesh object and export smooth surface """

    surface = TMesh(data)
    surface.smooth()


def solidify(data=None, totalDist=1, offset=1):
    """ Create a TMesh object and solidify objects """
    surface = TMesh(data)
    surface.solidify(totalDist, offset)
