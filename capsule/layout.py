# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Layout class definition."""

from collections import Counter


class Layout(object):
  """Base class for all layouts.

  Includes the view hierarchy, screenshot, and information about views and
  their resulting layouts.
  """

  def __init__(self, activity, frag_list, hierarchy, screenshot, num):
    """Constructor for Layout class."""
    self.activity = activity
    self.frag_list = frag_list
    self.hierarchy = hierarchy
    self.screenshot = screenshot
    self.num = num
    self.clickable = []
    self.preceding = []
    self.click_dict = {}

  def get_name(self):
    """Returns the identifying name of the Layout."""
    try:
      if self.frag_list:
        return self.activity + '-' + self.frag_list[0] + '-' + str(self.num)
      else:
        return self.activity + '-NoFrags-' + str(self.num)
    except TypeError:
      print 'Not a valid layout.'
      return ''

  def num_views(self):
    return len(self.hierarchy)

  def is_duplicate(self, activity, frag_list, hierarchy):
    """Determines if the passed-in information is identical to this Layout."""

    # Since the fragment names are hashable, this is the most efficient method
    # to compare two unordered lists according to
    # http://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
    # We also use it below to compare hierarchy ids.
    if (self.activity != activity or
        Counter(self.frag_list) != Counter(frag_list)):
      return False

    if self.num_views() != len(hierarchy):
      return False

    hierarchy_ids = [h['uniqueId'] for h in self.hierarchy]
    layout_ids = [h['uniqueId'] for h in hierarchy]

    return Counter(hierarchy_ids) == Counter(layout_ids)

  def is_duplicate_layout(self, other_layout):
    """Determines if the passed-in Layout is identical to this Layout."""
    if (self.activity != other_layout.activity or
        Counter(self.frag_list) != Counter(other_layout.frag_list)):
      return False

    if self.num_views() != len(other_layout.hierarchy):
      return False

    hierarchy_ids = [h['uniqueId'] for h in self.hierarchy]
    other_layout_ids = [ov['uniqueId'] for ov in other_layout.hierarchy]

    return Counter(hierarchy_ids) == Counter(other_layout_ids)

  def print_info(self):
    """Prints out information about the layout."""
    print 'Activity: ' + self.activity
    print 'Fragment: ' + self.frag_list
    print 'Num: ' + str(self.num)
    print 'Screenshot path:' + self.screenshot
    print 'Hierarchy: '
    for view in self.hierarchy:
      print view.getUniqueId()
