#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import json
from json import JSONDecodeError

from wtforms.validators import EqualTo, ValidationError

from airflow.utils import helpers


class GreaterEqualThan(EqualTo):
    """Compares the values of two fields.

    :param fieldname:
        The name of the other field to compare to.
    :param message:
        Error message to raise in case of a validation error. Can be
        interpolated with `%(other_label)s` and `%(other_name)s` to provide a
        more helpful error.
    """

    def __call__(self, form, field):
        try:
            other = form[self.fieldname]
        except KeyError:
            raise ValidationError(field.gettext(f"Invalid field name '{self.fieldname}'."))

        if field.data is None or other.data is None:
            return

        if field.data < other.data:
            message_args = {
                "other_label": hasattr(other, "label") and other.label.text or self.fieldname,
                "other_name": self.fieldname,
            }
            message = self.message
            if message is None:
                message = field.gettext(
                    f"Field must be greater than or equal to {message_args['other_label']}."
                )
            else:
                message = message % message_args

            raise ValidationError(message)


class ValidJson:
    """Validates data is valid JSON.

    :param message:
        Error message to raise in case of a validation error.
    """

    def __init__(self, message=None):
        self.message = message

    def __call__(self, form, field):
        if field.data:
            try:
                json.loads(field.data)
            except JSONDecodeError as ex:
                message = self.message or f"JSON Validation Error: {ex}"
                raise ValidationError(message=field.gettext(message.format(field.data)))


class ValidKey:
    """
    Validates values that will be used as keys

    :param max_length:
        The maximum length of the given key
    """

    def __init__(self, max_length=200):
        self.max_length = max_length

    def __call__(self, form, field):
        if field.data:
            try:
                helpers.validate_key(field.data, self.max_length)
            except Exception as e:
                raise ValidationError(str(e))
