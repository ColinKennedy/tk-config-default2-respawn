# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import math

import hiero

class CollatingExporter(object):
    def __init__(self, properties=None):
        super(CollatingExporter, self).__init__()

        # When building a collated sequence, everything is offset by 1000
        # This gives head room for shots which may go negative when transposed to a
        # custom start frame. This offset should be negated during script generation.
        self.HEAD_ROOM_OFFSET = 1000

        self._parentSequence = None
        self._collate = False
        self._hero = False
        self._heroItem = None
        self._collatedItemsMap = {}

        self._effects = []
        self._annotations = []
        self._collatedSequenceOutputFormat = None

        # Handles from the collated sequence.  This is set as a tuple if a collated sequence is created
        self._collatedSequenceHandles = None

        # Need to keep track of the master track item for disconnected sequence export
        self._masterTrackItemCopy = None

        # Default this to True.  If the following tests fail and return early, we want it in that state.
        # Maybe it would be better to raise an exception or something?
        self._nothingToDo = True

        # If skip offline is True and the input track item is offline, return
        if isinstance(self._item, hiero.core.TrackItem):
            if not self._source.isMediaPresent() and self._skipOffline:
                return

        # Check if this task is enabled.  Some tasks in a preset might be selectively disabled
        # when re-exporting
        #if not self._preset.properties()["enable"]:
        #    return

        # All clear.
        self._nothingToDo = False

        if properties is None:
            properties = self._preset.properties()

        if isinstance(self._item, hiero.core.TrackItem):
            # Build list of collated shots
            self._collatedItems = self._collatedItems(properties)

            # Only build sequence if there are multiple shots
            if len(self._collatedItems) > 1:
                self._collate = True

                if self._has_nuke_backend():
                    # Find all the effects which apply to collated items
                    from hiero.exporters import FnEffectHelpers
                    self._effects, self._annotations = FnEffectHelpers.findEffectsAnnotationsForTrackItems(self._collatedItems)

                # Build the sequence of collated shots
                self._buildCollatedSequence(properties)
            else:
                if self._has_nuke_backend():
                    # Find the effects which apply to this item.  Note this function expects a list.
                    from hiero.exporters import FnEffectHelpers
                    self._effects, self._annotations = FnEffectHelpers.findEffectsAnnotationsForTrackItems( [self._item] )

    def _offsetTimelineLinked(self, trackItem, offset):
        """
        Offset timeline for trackitem and it's linked audio items (since each video track is processed separately)
        """
        trackItem.setTimelineOut(trackItem.timelineOut() + offset)
        trackItem.setTimelineIn(trackItem.timelineIn() + offset)

        for item in trackItem.linkedItems():
            if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                item.setTimelineOut(item.timelineOut() + offset)
                item.setTimelineIn(item.timelineIn() + offset)

    def _trimInLinked(self, trackitem, value):
        """
        Trim In trackitem and it's linked audio items (since each video track is processed separately)
        """
        trackitem.trimIn(value)
        for item in trackitem.linkedItems(): 
            if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                item.trimIn(value)

    def _trimOutLinked(self, trackitem, value):
        """
        Trim Out trackitem and it's linked audio items (since each video track is processed separately)
        """
        trackitem.trimOut(value)
        for item in trackitem.linkedItems(): 
            if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                item.trimOut(value)

    def _collatedItems(self, properties):
        """
        Build and return list of collated shots, the CollateTracks option includes overlapping and identically named shots.
        CollateSequence Option includes all shots in parent sequence.
        """
        collatedItems = []

        collateTime = properties["collateTracks"]
        collateName = properties["collateShotNames"]

        if properties["collateSequence"]:
            # Add all trackitems to collate list
            for track in self._sequence.videoTracks():
                for trackitem in track:
                    collatedItems.append(trackitem)

        elif collateName or collateTime:
            nameMatches = [self._item]
            orderedMatches = []

            if collateName:
                # The collate tracks option will detect any trackitems on other tracks which overlap
                # so they can be included in the nuke script.
                for track in self._sequence.videoTracks():
                    for trackitem in track:
                        if trackitem is not self._item:
                            # Collate if shot name matches.
                            if trackitem.name() == self._item.name():
                                nameMatches.append(trackitem)
                                continue
            for track in self._sequence.videoTracks():
                for trackitem in track:
                    for nameMatchTrackItem in nameMatches:
                        if collateTime:
                            # Starts before or at same time
                            if trackitem.timelineIn() <= nameMatchTrackItem.timelineIn():
                                # finishes after start
                                if trackitem.timelineOut() >= nameMatchTrackItem.timelineIn():
                                    orderedMatches.append(trackitem)
                                    break
                            elif trackitem.timelineIn() > nameMatchTrackItem.timelineIn():
                                # Starts before end
                                if trackitem.timelineIn() < nameMatchTrackItem.timelineOut():
                                    orderedMatches.append(trackitem)
                                    break
                        elif trackitem == nameMatchTrackItem:
                            orderedMatches.append(trackitem)
                            break
            collatedItems = orderedMatches
        return collatedItems

    def _buildCollatedSequence(self, properties):
        """
        Build a sequence form a list of collated items.

        Delegates to the appropriate logic based on the current version of
        Hiero.
        """

        if self._has_nuke_backend():
            # later version of Hiero with nuke backend
            self._buildCollatedSequence_nuke(properties)
        else:
            # pre-nuke Hiero
            self._buildCollatedSequence_legacy(properties)

    def _buildCollatedSequence_legacy(self, properties):
        """
        From the list of collated Items build a sequence, extend edge shots for
        handles, offset relative to custom start or master shot source frame.

        This code runs on pre-nuke versions of Hiero.
        """
        if not self._collate or not self._collatedItems:
            return

        # Hero item for a collated sequence is the first one on the highest track
        def keyFunc(item):
            return ((sys.maxint - item.timelineIn()) * 1000) + item.parent().trackIndex()
        heroItem = max(self._collatedItems, key=keyFunc)
        self._hero = (heroItem.guid() == self._item.guid())
        self._heroItem = heroItem

        # Build a new sequence from the collated items
        newSequence = hiero.core.Sequence(self._item.name())

        # Copy tags from sequence to clone
        for tag in self._sequence.tags():
            newSequence.addTag(hiero.core.Tag(tag))

        # Apply the format of the master shot to the whole sequence
        # NOTE: Shouldn't it be taken from self._sequence instead? Multiple clips can have different resolution/formats
        newSequence.setFormat(self._clip.format())
        
        # Note: Without correct framerate, audio comes out silent when manually exporting the sequence.
        newSequence.setFramerate(self._clip.framerate())

        offset = self._item.sourceIn() - self._item.timelineIn()
        if self._startFrame is not None:
            # This flag indicates that an explicit start frame has been specified
            # To make sure that when the shot is expanded to include handles this is still the first
            # frame, here we offset the start frame by the in-handle size
            if properties["collateCustomStart"] and self._cutHandles is not None:
                self._startFrame += self._cutHandles

            # The offset required to shift the timeline position to the custom start frame.
            offset = self._startFrame - self._item.timelineIn()

        sequenceIn, sequenceOut = sys.maxint, 0
        for trackitem in self._collatedItems:
            if trackitem.timelineIn() <= sequenceIn:
                sequenceIn = trackitem.timelineIn()
            if trackitem.timelineOut() >= sequenceOut:
                sequenceOut = trackitem.timelineOut()

        newTracks = {}
        audioTracks = {}
        for trackitem in self._collatedItems:
            parentTrack = trackitem.parentTrack()

            # Clone each track and add it to a dictionary, using guid as key
            if parentTrack.guid() not in newTracks:
                trackClone = hiero.core.VideoTrack(parentTrack.name())
                newTracks[parentTrack.guid()] = trackClone
                newSequence.addTrack(trackClone)

                # Copy tags from track to clone
                for tag in parentTrack.tags():
                    trackClone.addTag(hiero.core.Tag(tag))

            trackItemClone = _clone_item(trackitem)
            self._collatedItemsMap[trackitem.guid()] = trackItemClone
            
            # Copy audio for track item
            linkedItems = trackitem.linkedItems()
            newAudio = {}
            for item in linkedItems:
                if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                    audioParentTrack = item.parentTrack()

                    if audioParentTrack.guid() not in audioTracks:
                        audioTrackClone = hiero.core.AudioTrack(audioParentTrack.name())
                        audioTracks[audioParentTrack.guid()] = audioTrackClone
                        newSequence.addTrack(audioTrackClone)

                        # Copy tags from track to clone
                        for tag in audioParentTrack.tags():
                            audioTrackClone.addTag(hiero.core.Tag(tag))
                    
                    audioItemClone = _clone_item(item)
                    trackItemClone.link(audioItemClone)

                    self._collatedItemsMap[item.guid()] = audioItemClone
                    
                    if audioParentTrack.guid() not in newAudio: 
                        newAudio[audioParentTrack.guid()] = []
                    newAudio[audioParentTrack.guid()].append(audioItemClone)

            # extend any shots
            if self._cutHandles is not None:
                # Maximum available handle size
                handleInLength, handleOutLength = trackitem.handleInLength(), trackitem.handleOutLength()
                # Clamp to desired handle size
                handleIn, handleOut = min(self._cutHandles, handleInLength), min(self._cutHandles, handleOutLength)

                if trackItemClone.timelineIn() <= sequenceIn and handleIn:
                    self._trimInLinked(trackItemClone, -handleIn)
                    hiero.core.log.debug("Expanding %s in by %i frames" % (trackItemClone.name(), handleIn))
                if trackItemClone.timelineOut() >= sequenceOut and handleOut:
                    self._trimOutLinked(trackItemClone, -handleOut)
                    hiero.core.log.debug("Expanding %s out by %i frames" % (trackItemClone.name(), handleOut))

            self._offsetTimelineLinked(trackItemClone, self.HEAD_ROOM_OFFSET + offset)

            # Add Cloned track item to cloned track
            try:
                newTracks[parentTrack.guid()].addItem(trackItemClone)
                for trackGuid in newAudio.keys():
                    for item in newAudio[trackGuid]:
                        audioTracks[trackGuid].addItem(item)
            except Exception as e:
                clash = newTracks[parentTrack.guid()].items()[0]
                error = "Failed to add shot %s (%i - %i) due to clash with collated shots, This is likely due to the expansion of the master shot to include handles. (%s %i - %i)\n" % (trackItemClone.name(), trackItemClone.timelineIn(), trackItemClone.timelineOut(), clash.name(), clash.timelineIn(), clash.timelineOut())
                self.setError(error)
                hiero.core.log.error(error)
                hiero.core.log.error(str(e))

        handles = self._cutHandles if self._cutHandles is not None else 0

        # Use in/out point to constrain output framerange to track item range
        newSequence.setInTime(max(0, (sequenceIn + offset + self.HEAD_ROOM_OFFSET) - handles))
        newSequence.setOutTime((sequenceOut + offset + self.HEAD_ROOM_OFFSET) + handles)

        # Copy posterFrame from Hero item to sequence
        base = heroItem.source()
        if isinstance(base, hiero.core.SequenceBase):
            posterFrame = base.posterFrame()
            if posterFrame:
                newSequence.setPosterFrame(heroItem.timelineIn() + posterFrame + self.HEAD_ROOM_OFFSET + offset)

        # Useful for debugging, add cloned collated sequence to Project
        #hiero.core.projects()[-1].clipsBin().addItem(hiero.core.BinItem(newSequence))

        # Use this newly built sequence instead
        self._parentSequence = self._sequence

        # Need to use the sequence clone here, otherwise audio becomes silent for unknown reasons.
        self._sequence = _clone_item(newSequence)

    def _buildCollatedSequence_nuke(self, properties):
        """
        From the list of collated Items build a sequence, extend edge shots for
        handles, offset relative to custom start or master shot source frame

        This code runs in later versions of Hiero with access to the nuke api.
        """

        # TODO: This code was pulled in from Hiero 10 source. The previous code
        # used to build the collate sequence had support for audio collation
        # as well. We need to add that code here and test to make sure it is
        # working as expected.

        if not self._collate:
            return

        # local imports to prevent exception in older versions of Hiero
        import itertools
        from hiero.core import EffectTrackItem
        from hiero.core.FnNukeHelpers import offsetNodeAnimationFrames
        from hiero.exporters.FnNukeShotExporter import NukeShotExporter
        import hiero.core.nuke as nuke

        # Hero item for a collated sequence is the first one on the highest track
        def keyFunc(item):
            return ((sys.maxint - item.timelineIn()) * 1000) + item.parent().trackIndex()
        heroItem = max(self._collatedItems, key=keyFunc)
        self._hero = (heroItem.guid() == self._item.guid())
        self._heroItem = heroItem

        # When building a collated sequence, everything is offset by 1000
        # This gives head room for shots which may go negative when transposed to a
        # custom start frame. This offset is negated during script generation.
        headRoomOffset = NukeShotExporter.kCollatedSequenceFrameOffset

        # Build a new sequence from the collated items
        newSequence = hiero.core.Sequence(self._sequence.name())

        # Copy tags from sequence to copy
        for tag in self._sequence.tags():
            newSequence.addTag(hiero.core.Tag(tag))

        # If outputting sequence time, we want the items to remain where they are on the sequence, offset should be 0
        if self.outputSequenceTime():
            offset = 0
        else:
            offset = self._item.sourceIn() - self._item.timelineIn()
            if self._startFrame is not None:
                # This flag indicates that an explicit start frame has been specified
                # To make sure that when the shot is expanded to include handles this is still the first
                # frame, here we offset the start frame by the in-handle size
                if properties["collateCustomStart"] and self._cutHandles is not None:
                #if  self._preset.properties()["collateCustomStart"]:
                    self._startFrame += self._cutHandles

                # The offset required to shift the timeline position to the custom start frame.
                offset = self._startFrame - self._item.timelineIn()

        # Copy the sequence properties.  Timecode start is offset so that track items have
        # the same timecode at their shifted timeline in.
        newSequence.setFormat(self._sequence.format())
        newSequence.setFramerate(self._sequence.framerate())
        newSequence.setDropFrame(self._sequence.dropFrame())
        newSequence.setTimecodeStart(self._sequence.timecodeStart() - (headRoomOffset + offset))

        sequenceIn, sequenceOut = sys.maxint, 0
        for trackitem in self._collatedItems:
            if trackitem.timelineIn() <= sequenceIn:
                sequenceIn = trackitem.timelineIn()
            if trackitem.timelineOut() >= sequenceOut:
                sequenceOut = trackitem.timelineOut()

        # Track the handles added
        sequenceInHandle = 0
        sequenceOutHandle = 0

        # Add tracks to the new sequence with tracks that match the original.  These will then be populated
        # with the items that should be exported.  They are stored in newTracks with the original guid as key, so
        # copied track items are added to the correct one.  There is also a list of unusedNewTracks, so any which
        # are not used can be removed at the end.
        unusedNewTracks = set()
        newTracks = {}
        for originalTrack in self._sequence.videoTracks():
            # Create new track
            newTrack = hiero.core.VideoTrack(originalTrack.name())
            newTracks[originalTrack.guid()] = newTrack
            unusedNewTracks.add(newTrack)
            newSequence.addTrack(newTrack)

            # Copy tags from track to copy
            for tag in originalTrack.tags():
                newTrack.addTag(hiero.core.Tag(tag))

            # Copy blending enabled flag
            newTrack.setBlendEnabled(originalTrack.isBlendEnabled())

        transitions = set()
        handleInAdjustments = {}
        handleOutAdjustments = {}

        linkedEffects = []

        for trackitem in self._collatedItems:
            parentTrack = trackitem.parentTrack()
            newTrack = newTracks[parentTrack.guid()]
            unusedNewTracks.discard(newTrack)

            # Build a list of transitions to be copied to the new sequence
            if trackitem.inTransition():
                transitions.add(trackitem.inTransition())
            if trackitem.outTransition():
                transitions.add(trackitem.outTransition())

            # Get the item's linked effects to be copied
            linkedEffects.extend( [ item for item in trackitem.linkedItems() if isinstance(item, hiero.core.EffectTrackItem) ] )

            trackItemCopy = trackitem.copy()

            # Need to keep track of the master track item for disconnected sequence exports
            if trackitem == self._item:
                self._masterTrackItemCopy = trackItemCopy

            # When writing a collated sequence, if any track items have their reformat state set to disabled,
            # use the largest source media format as the output format for the sequence.
            if trackitem.reformatState().type() == nuke.ReformatNode.kDisabled:
                sourceFormat = trackitem.source().format()
                if not self._collatedSequenceOutputFormat or (sourceFormat.width() > self._collatedSequenceOutputFormat.width() and sourceFormat.height() > self._collatedSequenceOutputFormat.height()):
                    self._collatedSequenceOutputFormat = sourceFormat

            # extend any shots
            if self._cutHandles is not None:
                # Maximum available handle size
                handleInLength, handleOutLength = trackitem.handleInLength(), trackitem.handleOutLength()
                # Clamp to desired handle size
                handleIn, handleOut = min(self._cutHandles, handleInLength), min(self._cutHandles, handleOutLength)

                # Prevent in handle going negative. Calculating timelineIn + offset tells us where the item will sit on the
                # sequence, and thus how many frames of handles there are available before it would become negative (since
                # the start of the sequence is always frame 0)
                offsetTimelineIn = trackItemCopy.timelineIn() + offset
                if offsetTimelineIn < handleIn:
                    handleIn = max(0, offsetTimelineIn)

                if trackItemCopy.timelineIn() <= sequenceIn and handleIn:
                    sequenceInHandle = max(sequenceInHandle, handleIn)
                    trackItemCopy.trimIn(-handleIn)
                    # Store the handle adjustment so that the linked item can be resized
                    # to match the track item it's linked to. Otherwise the item copy
                    # will not get relinked to trackItemCopy when it is added to
                    # the video track.
                    for linkedItem in trackitem.linkedItems():
                        handleInAdjustments[linkedItem] = -handleIn
                    hiero.core.log.debug("Expanding %s in by %i frames" % (trackItemCopy.name(), handleIn))
                if trackItemCopy.timelineOut() >= sequenceOut and handleOut:
                    sequenceOutHandle = max(sequenceOutHandle, handleOut)
                    trackItemCopy.trimOut(-handleOut)
                    # Store the handle adjustment so that the linked item can be resized
                    # to match the track item it's linked to. Otherwise the item copy
                    # will not get relinked to trackItemCopy when it is added to
                    # the video track.
                    for linkedItem in trackitem.linkedItems():
                        handleOutAdjustments[linkedItem] = handleOut
                    hiero.core.log.debug("Expanding %s out by %i frames" % (trackItemCopy.name(), handleOut))

            trackItemCopy.setTimes(trackItemCopy.timelineIn() + headRoomOffset + offset, trackItemCopy.timelineOut() + headRoomOffset + offset,
                               trackItemCopy.sourceIn(), trackItemCopy.sourceOut())

            # Add copied track item to copied track
            try:
                newTrack.addItem(trackItemCopy)
            except Exception as e:
                clash = newTracks[parentTrack.guid()].items()[0]
                error = "Failed to add shot %s (%i - %i) due to clash with collated shots, This is likely due to the expansion of the master shot to include handles. (%s %i - %i)\n" % (trackItemCopy.name(), trackItemCopy.timelineIn(), trackItemCopy.timelineOut(), clash.name(), clash.timelineIn(), clash.timelineOut())
                self.setError(error)
                hiero.core.log.error(error)
                hiero.core.log.error(str(e))

        # Copy transitions to the new sequence
        for transition in transitions:
            parentTrack = transition.parentTrack()
            newTrack = newTracks[parentTrack.guid()]
            transitionCopy = transition.copy()
            transitionCopy.setTimelineOut(transitionCopy.timelineOut() + headRoomOffset + offset)
            transitionCopy.setTimelineIn(transitionCopy.timelineIn() + headRoomOffset + offset)
            newTrack.addTransition(transitionCopy)

        # Copy any effects and add them to the sequence.  We don't do anything with handles here,
        # the effects just have the same timeline duration as before.
        for subTrackItem in itertools.chain(self._effects, linkedEffects, self._annotations):
            parentTrack = subTrackItem.parentTrack()
            newTrack = newTracks[parentTrack.guid()]
            unusedNewTracks.discard(newTrack)

            subTrackIndex = _subTrackIndex(subTrackItem)

            subTrackItemCopy = subTrackItem.copy()
            inAdjustment = handleInAdjustments.get(subTrackItem, 0)
            outAdjustment = handleOutAdjustments.get(subTrackItem, 0)
            subTrackItemCopy.setTimelineOut(subTrackItemCopy.timelineOut() + headRoomOffset + offset + outAdjustment)
            subTrackItemCopy.setTimelineIn(subTrackItemCopy.timelineIn() + headRoomOffset + offset + inAdjustment)

            # Offset the soft effects key frames by 1000
            if isinstance( subTrackItemCopy , EffectTrackItem ):
                effectTrackNode = subTrackItemCopy.node()
                offsetNodeAnimationFrames( effectTrackNode , headRoomOffset + offset);

            try:
                newTrack.addSubTrackItem(subTrackItemCopy, subTrackIndex)
            except:
                hiero.core.log.exception("NukeShotExporter._buildCollatedSequence failed to add effect")

        # Remove any empty tracks from the new sequence
        for track in unusedNewTracks:
            newSequence.removeTrack(track)

        # Use in/out point to constrain output framerange to track item range

        newSequence.setInTime(max(0, (sequenceIn + offset) - sequenceInHandle))
        newSequence.setOutTime((sequenceOut + offset) + sequenceOutHandle)

        # Copy posterFrame from Hero item to sequence
        base = heroItem.source()
        if isinstance(base, hiero.core.SequenceBase):
            posterFrame = base.posterFrame()
            if posterFrame:
                newSequence.setPosterFrame(heroItem.timelineIn() + posterFrame + self.HEAD_ROOM_OFFSET + offset)

        self._collatedSequenceHandles = (sequenceInHandle, sequenceOutHandle)

        # Useful for debugging, add copied collated sequence to Project
        #newSequence.setName("Collated Sequence")
        #hiero.core.projects()[-1].clipsBin().addItem(hiero.core.BinItem(newSequence))

        # Use this newly built sequence instead
        self._parentSequence = self._sequence
        self._sequence = newSequence

    def isCollated(self):
        return self._collate

    def originalSequence(self):
        return self._parentSequence

    def isHero(self):
        return self._hero

    def heroItem(self):
        return self._heroItem

    def finishTask(self):
        self._parentSequence = None

    def collatedOutputRange(self, ignoreHandles=False, ignoreRetimes=True, clampToSource=True, adjustForCustomStart=True):
        """Returns the output file range (as tuple) for this task, if applicable"""
        start = 0
        end  = 0

        if isinstance(self._item, hiero.core.Sequence) or self._collate:
            start, end = 0, self._item.duration() - 1

            if adjustForCustomStart and self._startFrame is not None:
                start += self._startFrame
                end += self._startFrame

            try:
                start = self._sequence.inTime()
            except RuntimeError:
                # This is fine, no in time set
                pass

            try:
                end = self._sequence.outTime()
            except RuntimeError:
                # This is fine, no out time set
                pass
        elif isinstance(self._item, (hiero.core.TrackItem, hiero.core.Clip)):
            # Get input frame range
            start, end = self.inputRange(ignoreHandles=ignoreHandles, ignoreRetimes=ignoreRetimes, clampToSource=clampToSource)

            if self._retime and isinstance(self._item, hiero.core.TrackItem) and ignoreRetimes:
                srcDuration = abs(self._item.sourceDuration())
                playbackSpeed = self._item.playbackSpeed()
                end = (end - srcDuration) + (srcDuration / playbackSpeed) + (playbackSpeed - 1.0)

            start = int(math.floor(start))
            end = int(math.ceil(end))

            # Offset by custom start time
            if adjustForCustomStart and self._startFrame is not None:
                end = self._startFrame + (end - start)
                start = self._startFrame

        return (start, end)

    def _has_nuke_backend(self):
        """
        Return ``True`` if this version of Hiero has a nuke backend.

        This method is typically used to determine which code path to take.

        Hiero versions have different behavior when it comes to writing frames
        to disk to account for handles without corresponding source material.
        Older versions (prior to nuke studio) will write black frames into the
        exported clip while newer versions will not.

        The collate logic is also different based on which version of hiero
        is being used.
        """

        if not hasattr(self, "_has_nuke"):

            try:
                import nuke
            except ImportError:
                # nuke failed to import. must be using a version of hiero
                # prior to 9.0 (nuke).
                self._has_nuke = False
            else:
                self._has_nuke = True

        return self._has_nuke


def _clone_item(item):
    """
    Older versions of hiero use clone() but it's deprecated in nukestudio in
    favor of copy().

    Use the appropriate method to clone the item.
    """

    if hasattr(item, "copy"):
        return item.copy()
    else:
        return item.clone()


def _subTrackIndex(subTrackItem):
    """
    Helper function to get the subtrack index for a subtrack item.
    TODO Should this go in the API?
    """
    track = subTrackItem.parentTrack()
    for index, subTrackItems in enumerate(track.subTrackItems()):
        if subTrackItem in subTrackItems:
            return index

class CollatedShotPreset(object):
    def __init__(self, properties):
        properties["collateTracks"] = False
        properties["collateShotNames"] = False

        # Not exposed in UI
        properties["collateSequence"] = False    # Collate all trackitems within sequence
        properties["collateCustomStart"] = True  # Start frame is inclusive of handles
