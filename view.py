"""View class definition."""

from collections import Counter


class View(object):
  """Base class for all views.

  Includes the view hierarchy, screenshot, and information about clickable
  components and their resulting views.
  """

  def __init__(self, activity, frag_list, hierarchy, screenshot, num):
    self.activity = activity
    self.frag_list = frag_list
    self.hierarchy = hierarchy
    self.screenshot = screenshot
    self.num = num
    self.clickable = []
    self.preceding = []

  def get_name(self):
    # Return the identifying name of the View (activity, fragment list, and
    # number).
    return [self.activity, self.frag_list, self.num]

  def num_components(self):
    return len(self.hierarchy)

  def is_duplicate(self, cv_activity, cv_frag_list, cv_hierarchy):
    """Determine if the passed-in current view is identical to this View."""

    # Since the fragment names are hashable, this is the most efficient method to
    # compare two unordered lists according to
    # http://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
    # We also use it below to compare hierarchy ids.
    if (self.activity != cv_activity or
        Counter(self.frag_list) != Counter(cv_frag_list)):
      return False

    if len(cv_hierarchy) != self.num_components():
      return False

    hierarchy_ids = [h['uniqueId'] for h in self.hierarchy]
    curr_view_ids = [cv['uniqueId'] for cv in cv_hierarchy]

    return Counter(hierarchy_ids) == Counter(curr_view_ids)

  def print_info(self):

    print 'Activity: ' + self.activity
    print 'Fragment: ' + self.frag_list
    print 'Num: " + str(self.num)'
    print 'Screenshot path:' + self.screenshot
    print 'Hierarchy: '
    for component in self.hierarchy:
      print component
