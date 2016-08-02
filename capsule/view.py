# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""View class definition."""

from collections import Counter


class View(object):
  """Base class for all views.

  Includes the view hierarchy, screenshot, and information about clickable
  components and their resulting views.
  """

  def __init__(self, activity, frag_list, hierarchy, screenshot, num):
    """Constructor for View class."""
    self.activity = activity
    self.frag_list = frag_list
    self.hierarchy = hierarchy
    self.screenshot = screenshot
    self.num = num
    self.clickable = []
    self.preceding = []
    self.click_dict = {}

  def get_name(self):
    """Returns the identifying name of the View."""
    try:
      if self.frag_list:
        return self.activity + '-' + self.frag_list[0] + '-' + str(self.num)
      else:
        return self.activity + '-NoFrags-' + str(self.num)
    except TypeError:
      print 'Not a valid view.'
      return ''

  def num_components(self):
    return len(self.hierarchy)

  def is_duplicate(self, activity, frag_list, hierarchy):
    """Determines if the passed-in information is identical to this View."""

    # Since the fragment names are hashable, this is the most efficient method
    # to compare two unordered lists according to
    # http://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
    # We also use it below to compare hierarchy ids.
    if (self.activity != activity or
        Counter(self.frag_list) != Counter(frag_list)):
      return False

    if self.num_components() != len(hierarchy):
      return False

    hierarchy_ids = [h['uniqueId'] for h in self.hierarchy]
    view_ids = [h['uniqueId'] for h in hierarchy]

    return Counter(hierarchy_ids) == Counter(view_ids)

  def is_duplicate_view(self, other_view):
    """Determines if the passed-in View is identical to this View."""
    if (self.activity != other_view.activity or
        Counter(self.frag_list) != Counter(other_view.frag_list)):
      return False

    if self.num_components() != len(other_view.hierarchy):
      return False

    hierarchy_ids = [h['uniqueId'] for h in self.hierarchy]
    other_view_ids = [ov['uniqueId'] for ov in other_view.hierarchy]

    return Counter(hierarchy_ids) == Counter(other_view_ids)

  def print_info(self):
    """Prints out information about the view."""
    print 'Activity: ' + self.activity
    print 'Fragment: ' + self.frag_list
    print 'Num: ' + str(self.num)
    print 'Screenshot path:' + self.screenshot
    print 'Hierarchy: '
    for component in self.hierarchy:
      print component.getUniqueId()
