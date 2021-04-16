from possum.pos_parameters import filename_parameter, value_parameter
from possum.pos_parameters import string_parameter, vector_parameter
from possum import pos_wrappers


class preprocess_slice_volume(pos_wrappers.generic_wrapper):
    _template = """pos_slice_volume \
            -i {input_image} \
            -o "{output_naming}" \
            -s {slicing_plane} \
            -r {start_slice} {end_slice} {step} \
            {shift_indexes}"""

    _parameters = {
            'input_image': filename_parameter('input_image', None),
            'output_naming': filename_parameter('output_naming', None),
            'slicing_plane': value_parameter('slicing_plane', 1),
            'start_slice': value_parameter('start_slice', None),
            'end_slice': value_parameter('end_slice', None),
            'step': value_parameter('step', 1),
            'shift_indexes': value_parameter(
                'output-filenames-offset', None,
                str_template="--{_name} {_value}"),
            'output_dir': string_parameter('output_dir', None),
            }


class blank_slice_deformation_wrapper(pos_wrappers.generic_wrapper):
    _template = """c{dimension}d  {input_image} -scale 0 -dup -omc {dimension} {output_image}"""
    _parameters = {
        'dimension': value_parameter('dimension', 2),
        'input_image': filename_parameter('input_image', None),
        'output_image': filename_parameter('output_image', None),
            }


class convert_slice_parent(pos_wrappers.generic_wrapper):
    _template = """ -- stub -- """

    _parameters = {
            'dimension': value_parameter('dimension', 2),
            'input_image': filename_parameter('input_image', None),
            'output_image': filename_parameter('output_image', None),
            'scaling': value_parameter('scaling', None, "-scale {_value}"),
            'spacing': vector_parameter('spacing', None, '-spacing {_list}mm')
            }


class convert_slice_image(convert_slice_parent):
    _template = """c{dimension}d -mcs {input_image}\
            -foreach {spacing} {scaling} -endfor \
            -omc {dimension} {output_image}"""


class convert_slice_image_grayscale(convert_slice_parent):
    _template = """c{dimension}d {input_image}\
                    {spacing} {scaling}\
                   -o {output_image}"""
