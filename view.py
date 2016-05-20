from collections import Counter

class View:
  """Base class for all views. Includes the view hierarchy, screenshot, and
     information about clickable components and their resulting views."""

  def __init__(self, activity, fragment):
    self.activity = activity
    self.fragment = fragment
    self.num = 0
    self.screenshot = ''
    self.hierarchy = []
    self.clickable = []
    self.preceding = []

  def get_name(self):
    # Return the identifying name of the View (activity, fragment, and number).
    return [self.activity, self.fragment, self.num]

  def num_components(self):
    return len(self.hierarchy)

  def is_duplicate(self, cv_activity, cv_fragment, cv_hierarchy):
    """Determine if the passed-in current view is identical to this View.
       Right now we do it by ensuring that the activity & fragment names are
       the same and that there is the same list of components in the view
       hierarchies."""

    if self.activity != cv_activity or self.fragment != cv_fragment:
      return False

    if len(cv_hierarchy) != self.num_components():
      return False

    hierarchy_ids = [h['uniqueId'] for h in self.hierarchy]

    curr_view_ids = [cv['uniqueId'] for cv in cv_hierarchy]

    # Since the unique ids are hashable, this is the most efficient method to
    # compare two unordered lists according to
    # http://stackoverflow.com/questions/7828867/how-to-efficiently-compare-two-unordered-lists-not-sets-in-python
    return Counter(hierarchy_ids) == Counter(curr_view_ids)

  def print_info(self):

    print "Activity: " + self.activity
    print "Fragment: " + self.fragment
    print "Num: " + str(self.num)
    print "Screenshot path:" + self.screenshot
    print "Hierarchy: "
    for component in self.hierarchy:
      print component