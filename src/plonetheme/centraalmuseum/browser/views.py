from Acquisition import aq_inner, aq_parent
from Products.Five import BrowserView
from plone.app.multilingual.subscriber import createdEvent

from collective.leadmedia.utils import addCropToTranslation
from plone.app.multilingual.interfaces import ITranslatable
from plone.app.multilingual.interfaces import ITranslationManager

from plone.app.contenttypes.browser.collection import CollectionView
from plone.app.uuid.utils import uuidToCatalogBrain
from plone.event.interfaces import IEvent

from datetime import date
from DateTime import DateTime
import time

from plone.app.event.browser.event_listing import EventEventListing, EventListing, EventListingIcal
import plone.api
from zope.component import getMultiAdapter
from plone.event.interfaces import IEvent
from zope.contentprovider.interfaces import IContentProvider

from bs4 import BeautifulSoup as BSHTML
import re

class ContextToolsView(BrowserView):

    def get_img_tags(self, data):
        soup = BSHTML(data)
        images = soup.findAll('img')
        if images:
            image = images[0]
            src = image['src']
            return src
        return ''

    def remove_img_tags(self, data):
        p = re.compile(r'<img.*?/>')
        return p.sub('', data)

    def getSlideStyles(self, item, slide_style="text-only"):
        text = getattr(item, 'text', None)
        text_output = text.output

        styles = ""

        if slide_style == "image-slide":
            img_source = self.get_img_tags(text_output)

            styles = ""

            if img_source:
                styles = "background-image: url(%s);" %(img_source)
            else:
                styles = ""

        return styles
        
    def getSlideBodyText(self, item, slide_type="text-only"):
        text = getattr(item, 'text', None)

        if slide_type == "image-slide":
            new_text = self.remove_img_tags(text.output)
            return new_text

        output_text = getattr(text, 'output', '')
        return output_text

    def getSlideType(self, item):
        text = getattr(item, 'text', None)
        if text:

            if "side-text" in getattr(item, 'id', ''):

                if "image-left" in getattr(text, 'raw', ''):
                    return "side-text-slide left"
                elif "image-right" in getattr(text, 'raw', ''):
                    return "side-text-slide right"
                else:
                    return "side-text-slide"
            
            elif "<img" in getattr(text, 'raw', ''):
                return "image-slide"

            elif "<iframe" in getattr(text, 'raw', ''):
                return "video-slide"
            else:
                return "text-only"
        else:
            return ""


    def hasPresentation(self, item):
        try:
            if 'presentation' in item:
                presentation_folder = item['presentation']
                state = plone.api.content.get_state(obj=presentation_folder)
                if state != 'published':
                    return False
                else:
                    return True
        except:
            raise

        return False

    def getPresentationItems(self, item):
        folder_contents = None
        if 'presentation' in item:
            presentation_folder = item['presentation']
            contents = presentation_folder.getFolderContents()
            folder_contents = [item for item in contents if getattr(item, 'portal_type', '') == 'Document']

        return folder_contents

    def getImageObject(self, item, scale="large"):
        if item.portal_type == "Image":
            return item.getURL()+"/@@images/image/%s" %(scale)
        if item.leadMedia != None:
            uuid = item.leadMedia
            media_object = uuidToCatalogBrain(uuid)
            if media_object:
                return media_object.getURL()+"/@@images/image/%s" %(scale)
            else:
                return None
        else:
            return None

    def getImageBrain(self, item):
        img_brain = None

        if item.portal_type == "Image":
            return item
        
        if getattr(item, 'leadMedia', None) not in [None, '']:
            uuid = item.leadMedia
            media_object = uuidToCatalogBrain(uuid)
            if media_object:
                return media_object
            else:
                return None
        else:
            return None

    def is_event(self, obj):
        if getattr(obj, 'getObject', False):
            obj = obj.getObject()
        return IEvent.providedBy(obj)

    def isAnonymous(self):
        annon = True
        if not plone.api.user.is_anonymous():
            return False

        return annon

    def formatted_date(self, obj):
        item = obj.getObject()
        provider = getMultiAdapter(
            (self.context, self.request, self),
            IContentProvider, name='formatted_date'
        )
        return provider(item)

    def isSlideshowPublished(self, item):
        obj = item.getObject()
        slideshow = obj.get('slideshow', None)
        
        if slideshow:
            slideshow_brain = uuidToCatalogBrain(slideshow.UID())
            if slideshow_brain:
                if slideshow_brain.review_state != 'published':
                    return False
                else:
                    return True
            else:
                return True
        else:
            return True

    def isEventPast(self, event):
        """ Checks if the event is already past """
        if event.portal_type != 'Event':
            return False
        else:
            try:
                t = DateTime(time.time())
                if event.end is not None:
                    end = DateTime(event.end)
                    return end.year() < t.year() or (end.year() == t.year() and end.month() < t.month()) or(end.year() == t.year() and end.month() == t.month() and end.day() < t.day())
                else:
                    start = DateTime(event.start)
                    return start.year() < t.year() or (start.year() == t.year() and start.month() < t.month()) or(start.year() == t.year() and start.month() == t.month() and start.day() < t.day())
            except:
                return False
        return True

class OnlineExperienceView(CollectionView):

    def find_orientation(self, item):
        if type(item) == str:
            if item == "L":
                return "landscape"
            else:
                return "portrait"

        item_class = ""
        if item.portal_type == "Image":
            image_obj = item.getObject()
            if getattr(image_obj, 'image', None):
                try:
                    w, h = image_obj.image.getImageSize()
                    if w > h:
                        item_class = "%s" %('landscape')
                    else:
                        item_class = "%s" %('portrait')
                except:
                    return item_class
        elif item.hasMedia:
            image = uuidToCatalogBrain(item.leadMedia)
            if image:
                image_obj = image.getObject()
                if getattr(image_obj, 'image', None):
                    try:
                        w, h = image_obj.image.getImageSize()
                        if w > h:
                            item_class = "%s" %('landscape')
                        else:
                            item_class = "%s" %('portrait')
                    except:
                        return item_class

        return item_class

    def getImageProperties(self, item):
        link = item.getURL()+"/view"
        title = item.Title
        description = item.Description

        try:
            if item.portal_type == "Image":
                image = item.getObject()
                parent = image.aq_parent
                if parent.portal_type == "Folder":
                    if parent.id == "slideshow":
                        obj = parent.aq_parent
                        if obj.portal_type == "Object":
                            title = obj.title
                            description = obj.description
                            link = obj.absolute_url()

        except:
            raise

        return {"link": link, "title": title, "description": description}

    def pairItems(self, results):
        # L P L L L P P P
        TEST_INPUT = ["L", "P", "L", "L", "L", "P", "P", "P"]
        FIRST_ITEM = 0
        
        items = results
        sequence_items = items._sequence
        total_items = len(sequence_items)
        items_checked = []
        final_patterns = []

        right = True
        previous_pair = ""

        for i in range(total_items):

            if i not in items_checked:

                right_pattern = "right" if right else "left"
                pattern = {
                    "size": "small",
                    "orientation": self.find_orientation(sequence_items[i]),
                    "position": "pair",
                    "clearfix": False,
                    "item": sequence_items[i],
                    "right": right_pattern,
                    "bottom": ""
                }
               
                if i == FIRST_ITEM:
                    pattern['position'] = "single"
                    pattern['size'] = "big"
                    final_patterns.append(pattern)
                    items_checked.append(i)
                    if right:
                        right = False
                    else:
                        right = True
                else:
                    if i+1 < total_items:
                        next_orientation = self.find_orientation(sequence_items[i+1])

                        if next_orientation == pattern["orientation"] == "landscape":
                            pattern["position"] = "single"
                            pattern["size"] = "big"
                            final_patterns.append(pattern)
                            if right:
                                right = False
                            else:
                                right = True

                            previous_pair = ""
                        else:
                            new_pattern = {
                                "size": pattern['size'],
                                "orientation": pattern['orientation'],
                                "position": "pair",
                                "clearfix": True,
                                "item": sequence_items[i+1],
                                "right": pattern['right'],
                                "bottom": pattern['bottom']
                            }
                            new_pattern["orientation"] = next_orientation

                            if next_orientation == pattern['orientation'] == "portrait":
                                pattern['size'] = "big"
                                new_pattern['size'] = "big"

                            if not previous_pair:
                                if right:
                                    pattern['bottom'] = "bottom"
                                    new_pattern['bottom'] = "up"
                                else:
                                    new_pattern['bottom'] = "bottom"
                                    pattern['bottom'] = "up"
                            else:
                                if previous_pair == "bottom":
                                    pattern['bottom'] = "up"
                                    new_pattern['bottom'] = "bottom"
                                    previous_pair = "bottom"
                                else:
                                    pattern['bottom'] = "bottom"
                                    new_pattern['bottom'] = "up"
                                    previous_pair = "up"

                            final_patterns.append(pattern)
                            final_patterns.append(new_pattern)
                            items_checked.append(i)
                            items_checked.append(i+1)
                    else:
                        pattern['position'] = "single"
                        pattern['size'] = "big"
                        final_patterns.append(pattern)
            else:
                pass

        return final_patterns


    def getImageObject(self, item):
        if item.portal_type == "Image":
            return item.getURL()+"/@@images/image/large"
        if item.leadMedia != None:
            uuid = item.leadMedia
            media_object = uuidToCatalogBrain(uuid)
            if media_object:
                return media_object.getURL()+"/@@images/image/large"
            else:
                return None
        else:
            return None

    def getImageClass(self, item, has_media=False):

        item_class = "entry"

        if item.portal_type == "Image":
            image_obj = item.getObject()
            if getattr(image_obj, 'image', None):
                try:
                    w, h = image_obj.image.getImageSize()
                    if w > h:
                        item_class = "%s %s" %(item_class, 'landscape')
                    else:
                        item_class = "%s %s" %(item_class, 'portrait')
                except:
                    return item_class
        elif has_media:
            image = uuidToCatalogBrain(item.leadMedia)
            image_obj = image.getObject()
            if getattr(image_obj, 'image', None):
                try:
                    w, h = image_obj.image.getImageSize()
                    if w > h:
                        item_class = "%s %s" %(item_class, 'landscape')
                    else:
                        item_class = "%s %s" %(item_class, 'portrait')
                except:
                    return item_class

        return item_class


class FullScreenCollectionView(CollectionView):

    def getLeadMediaURL(self, item, scale="large"):
        if item.portal_type == "Image":
            url = item.getURL()
            if url:
                return "%s/@@images/image/%s" %(item.getURL(), scale)
            else:
                return None
        if item.leadMedia != None:
            media_object = uuidToCatalogBrain(item.leadMedia)
            if media_object:
                return "%s/@@images/image/%s" %(media_object.getURL(), scale)
            else:
                return None
        return None



class CustomEventEventListing(EventEventListing):
    def getLeadMedia(self, brain):
            
        acc_context = brain.context
        lead_obj = acc_context
        if getattr(acc_context, 'portal_type', None) == "Occurrence":
            lead_obj = aq_parent(aq_inner(acc_context))

        item = uuidToCatalogBrain(lead_obj.UID())

        if item.portal_type == "Image":
            return item.getURL()+"/@@images/image/mini"
        
        if item.leadMedia != None:
            uuid = item.leadMedia
            media_object = uuidToCatalogBrain(uuid)
            if media_object:
                return media_object.getURL()+"/@@images/image/mini"
            else:
                return None
        else:
            return None

        return ""

class CustomEventListing(EventListing):
    def getLeadMedia(self, brain):
            
        acc_context = brain.context
        lead_obj = acc_context
        if getattr(acc_context, 'portal_type', None) == "Occurrence":
            lead_obj = aq_parent(aq_inner(acc_context))

        item = uuidToCatalogBrain(lead_obj.UID())

        if item.portal_type == "Image":
            return item.getURL()+"/@@images/image/mini"
        
        if item.leadMedia != None:
            uuid = item.leadMedia
            media_object = uuidToCatalogBrain(uuid)
            if media_object:
                return media_object.getURL()+"/@@images/image/mini"
            else:
                return None
        else:
            return None

        return ""


class CustomEventListingIcal(EventListingIcal):
    pass


def objectTranslated(ob, event):
    if ob:
        if ITranslatable.providedBy(ob):
            if getattr(ob, 'language', None) == "en" and getattr(ob, 'portal_type', None) in ["Document", "Event"]:
                createdEvent(ob, event)
                if not hasattr(ob, 'slideshow'):
                    if ITranslationManager(ob).has_translation('nl'):
                        original_ob = ITranslationManager(ob).get_translation('nl')
                        
                        if hasattr(original_ob, 'slideshow'):
                            slideshow = original_ob['slideshow']
                            ITranslationManager(slideshow).add_translation('en')
                            slideshow_trans = ITranslationManager(slideshow).get_translation('en')
                            slideshow_trans.title = slideshow.title
                            slideshow_trans.portal_workflow.doActionFor(slideshow_trans, "publish", comment="Slideshow published")
                            
                            for sitem in slideshow:
                                if slideshow[sitem].portal_type == "Image":
                                    ITranslationManager(slideshow[sitem]).add_translation('en')
                                    trans = ITranslationManager(slideshow[sitem]).get_translation('en')
                                    trans.image = slideshow[sitem].image
                                    addCropToTranslation(slideshow[sitem], trans)

                            ob.reindexObject()
                            ob.reindexObject(idxs=["hasMedia"])
                            ob.reindexObject(idxs=["leadMedia"])
                        else:
                            # no slideshow folder
                            pass
                    else:
                        # no translation
                        pass
                else:
                    # has slideshow
                    pass
            else:
                # wrong language
                pass
    else:
        # invalid object
        pass

    return


