from __future__ import unicode_literals

import os

from mopidy import config, ext


__version__ = '0.1'


class Extension(ext.Extension):
    dist_name = 'Mopidy-Snapcast'
    ext_name = 'snapcast'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['host'] = config.String()
        schema['port'] = config.Integer()
        schema['group_id'] = config.String(optional=True)
        return schema

    def setup(self, registry):
        from .mixer import SnapcastMixer
        registry.add('mixer', SnapcastMixer)
