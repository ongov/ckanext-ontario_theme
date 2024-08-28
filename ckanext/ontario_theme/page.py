u'''
Overrides CKAN's pagination.py module to be more accessbile
Replaces symbol_next and symbol_previous with single chevron
rather than double chevron to better align with current
pagination practices.
Adds aria-labels to each link in the pagination and
removes redundant links so users do not get confused
'''

import ckan.lib.pagination as pagination
import dominate.tags as tags
import re
from ckan.common import _
from markupsafe import Markup
from six import text_type


class Page(pagination.Page):
    symbol_next = '<svg class="ontario-icon" focusable="false" \
        aria-hidden="true" sol:category="primary" viewBox="0 0 \
            24 24" preserveAspectRatio="xMidYMid meet"> \
                <use href="#ontario-icon-chevron-right"></svg>'
    symbol_previous = '<svg class="ontario-icon" focusable="false" \
        aria-hidden="true" sol:category="primary" viewBox="0 0 24 24" \
            preserveAspectRatio="xMidYMid meet"> \
                <use href="#ontario-icon-chevron-left"></use></svg>'

    def pager(self, *args, **kwargs):
        with tags.div(cls="pagination-wrapper", role="navigation") as wrapper:
            tags.ul(
                "$link_previous ~2~ $link_next",
                cls="pagination",
                aria_label="pagination",
            )
        params = dict(
            format=text_type(wrapper),
            symbol_previous=Markup(Page.symbol_previous),
            symbol_next=Markup(Page.symbol_next),
            curpage_attr={"class": "active"},
            link_attr={},
        )
        params.update(kwargs)
        return super(pagination.Page, self).pager(*args, **params)

    def _pagerlink(self, page, text, extra_attributes=None):
        anchor = super(pagination.Page, self)._pagerlink(page, text)
        extra_attributes = extra_attributes or {}
        if page == self.page:
            anchor.set_attribute("aria-current", "page")
            anchor.set_attribute("aria-label", "page {}".format(page))
        elif text == Page.symbol_previous:
            anchor.set_attribute("aria-label", _("Go to previous page"))
            anchor.set_attribute("class", "pagination_symbols")
        elif text == Page.symbol_next:
            anchor.set_attribute("aria-label", _("Go to next page"))
            anchor.set_attribute("class", "pagination_symbols")
        else:
            anchor.set_attribute("aria-label", _("Go to page {}").format(page))
        return text_type(tags.li(anchor, **extra_attributes))

    def _range(self, regexp_match):
        html = super(pagination.Page, self)._range(regexp_match)
        # Convert '..'
        dotdot = u'<span class="pager_dotdot">..</span>'
        dotdot_link = tags.li(tags.span(u"..."), cls=u"disabled",
                              aria_hidden=u"true")
        html = re.sub(dotdot, text_type(dotdot_link), html)
        # Convert current page
        text = u"%s" % self.page
        current_page_span = text_type(tags.span(text, **self.curpage_attr))
        current_page_link = self._pagerlink(
            self.page, text, extra_attributes=self.curpage_attr
        )
        return re.sub(current_page_span, current_page_link, html)

    pagination.Page.pager = pager
    pagination.Page._pagerlink = _pagerlink
    pagination.Page._range = _range
