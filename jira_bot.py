import sys
from mattermostdriver import Driver
from collections import Counter
from jira import JIRA
from datetime import datetime
import urllib3
import json
import re
import webhook
import requests


def getAdjustDict():
    adjust_dict = {'h1\. ': '## ',
                   'h2\. ': '## ',
                   'h3\. ': '### ',
                   'h4\. ': '### ',
                   'h5\. ': '#### ',
                   'h6\. ': '#### ',
                   '\*(\w+)\*': '**\\1**',
                   '-(\w+)-': '~~\\1~~',
                   '\?\?(\w+)\?\?': '--\\1',
                   '{{(\w+)}}': '`\\1`',
                   '\[([\w \-\&":,;_\.\+]+)\|([\w\/\.:\-\?=&#\+]+)\]': '[\\1](\\2)',
                   ':\)': u'\u200b:smiley:\u200b',
                   ':\(': u'\u200b:worried:\u200b',
                   ':P': u'\u200b:stuck_out_tongue:\u200b',
                   ':D': u'\u200b:smile:\u200b',
                   '\;\)': u'\u200b:smirk:\u200b',
                   '\(y\)': u'\u200b:thumbsup:\u200b',
                   '\(n\)': u'\u200b:thumbsdown:\u200b',
                   '\(i\)': u'\u200b:information_source:\u200b',
                   '\(\/\)': u'\u200b:white_check_mark:\u200b',
                   '\(x\)': u'\u200b:x:\u200b',
                   '\(\!\)': u'\u200b:warning:\u200b',
                   '\(\?\)': u'\u200b:question:\u200b',
                   '\(\+\)': u'\u200b:heavy_plus_sign:\u200b',
                   '\(\-\)': u'\u200b:heavy_minus_sign:\u200b',
                   '\(on\)': u'\u200b:bulb:\u200b',
                   '\(off\)': u'\u200b:bulb: -off\u200b',
                   '\(\*\)': u'\u200b:star:\u200b',
                   '\(\*y\)': u'\u200b:star:\u200b',
                   '\n # ': '\n 1. ',
                   '(\![\w\-_\.äüö]+\.\w+\!)': '\\1'}
    return adjust_dict


def getCommentString():
    return ' \n{} **@{}**: \n {} \n\n Erstellt: {} \n Updated: {} \n\n'


def getAttachmentString():
    return '\n #### Folgende Anhänge wurden hinzugefügt: \n'


def getAssigneeString(currentAvatarLink, currentUsername):
    return '\n #### Bearbeiter: {} @{} \n'.format(currentAvatarLink, currentUsername)


def getAssigneeChangedString(oldAvatarLink, oldUsername, newAvatarLink, newUsername):
    return '\n #### Bearbeiter: von {} @{} zu {} @{} \n'.format(oldAvatarLink, oldUsername, newAvatarLink, newUsername)


def getIssueAndKeySummaryString():
    return '### {} [{}]({}): {} \n #### Status: {} \n #### Bearbeiter: {} {} \n'


def getTitleString(picture, issueAsString, linkToIssue, summary):
    return '### {} [{}]({}): {} \n'.format(picture, issueAsString, linkToIssue, summary)


def getIssueAndKeySummaryWDescriptionString():
    return '### {} [{}]({}): {} \n #### Status: {} \n #### Bearbeiter: {} {} \n\n #### Beschreibung: \n {}'


def getPictureString(linkToPic, hoverText):
    return '![Jira]({} =30x30 "{}")'.format(linkToPic, hoverText)


def getPictureStringWithLink(linkToPic, hoverText):
    return '\n [![{}]({} "{}")]({}) \n'.format(hoverText, linkToPic, hoverText, linkToPic)


def formatDate(date):
    return datetime.strptime(date[:-9], '%Y-%m-%dT%H:%M:%S')


def getTimestamp():
    return str(datetime.now())[:-16] + 'T' + str(datetime.now())[11:] + '00'


def sendMattermost(driver, text):
    driver.webhooks.call_webhook(webhook.token, {"channel": webhook.channel, "username": webhook.botName, "text": text})


def adjustSyntax(text):
    adjust = getAdjustDict()
    for key in adjust:
        text = re.compile(key).sub(adjust[key], text)
    return text


def sendIssueKeyAndSummary():
    assignee, status, avatar_url = getStatusAndAssignee()
    sendMattermost(driver, ''.join(getIssueAndKeySummaryString().format(
        getPictureString(issue.fields.priority.iconUrl, issue.fields.priority.name), issueAsString,
        webhook.jqlQueryString + issueAsString,
        str(
            issue.fields.summary),
        status, getPictureString(avatar_url + assignee, assignee),
        assignee)))


def sendIssueKeyAndSummaryWithDescription(description):
    assignee, status, avatar_url = getStatusAndAssignee()
    sendMattermost(driver, getIssueAndKeySummaryWDescriptionString().format(
        getPictureString(issue.fields.priority.iconUrl, issue.fields.priority.name), issueAsString,
        webhook.jqlQueryString + issueAsString,
        str(
            issue.fields.summary),
        status, getPictureString(avatar_url + assignee, assignee),
        assignee, description))


def checkForNewComments():
    if len(issue.fields.comment.comments) > 0:
        gen = (comment for comment in issue.fields.comment.comments if
               formatDate(comment.updated) > lastViewedFormatted)
        all_comments = [
            (comment.author.name, comment.body, comment.created, comment.updated)
            for comment in gen]
        assignee, status, avatar_url = getStatusAndAssignee()
        comments_selected = [
            getCommentString().format(getPictureString(avatar_url + author, assignee), author, adjustSyntax(body),
                                      formatDate(created),
                                      formatDate(updated))
            for (author, body, created, updated) in all_comments]
        issue_and_key_summary_string = getIssueAndKeySummaryString().format(
            getPictureString(issue.fields.priority.iconUrl, issue.fields.priority.name), issueAsString,
            webhook.jqlQueryString + issueAsString,
            str(issue.fields.summary), status,
            getPictureString(avatar_url + assignee, assignee),
            assignee)

        if len(comments_selected) > 0:
            sendMattermost(driver, issue_and_key_summary_string + seperator.join(comments_selected))


def getStatusAndAssignee():
    status = issue.fields.status.name
    assignee = issue.fields.assignee.key
    avatar_url = webhook.jiraUrl + 'secure/useravatar?ownerId='
    return assignee, status, avatar_url


def readJSON():
    with open(webhook.pathToFile, "r") as read_file:
        lastViewed = json.load(read_file)
    lastViewed = lastViewed["timestamp"]
    return lastViewed


def setTimestampJSONFile():
    file = {
        "timestamp": getTimestamp(),
    }
    return file


def writeJSON():
    with open(webhook.pathToFile, "w") as write_file:
        print("file = {}".format(str(file)))
        json.dump(file, write_file)


def checkAssigneeChanges(entry):
    global assignee_string
    assignee_mentioned = False
    if entry.field == 'assignee' and not assignee_mentioned:
        try:
            if entry.fromString != None:
                oldAssignee = jira.search_users(entry.fromString)[0].key
                assignee_string = getAssigneeChangedString(getPictureString(default_avatar_url + oldAssignee, oldAssignee),
                                                             oldAssignee,
                                                             getPictureString(default_avatar_url + assignee, assignee),
                                                             assignee)

                assignee_mentioned = True
        except JIRAError:
            print("Problems with checkAssigneeChanges! Details: Issue: {}; changelog:\n fromString: {} \n toString: {} ".format(issueAsString, entry.fromString, entry.toString))
    elif not assignee_mentioned:
        assignee_string = getAssigneeString(getPictureString(default_avatar_url + assignee, assignee), assignee)
    return assignee_string, assignee_mentioned


def checkAttachmentChanges(entry):
    global attachment_string
    if entry.field == 'Attachment':
        try:
            pictureString = entry.toString
            pictureID = entry.to
            attachmentObject = jira.attachment(pictureID)
            pictureURL = attachmentObject.content
            attachment_string += getPictureStringWithLink(pictureURL, pictureString)
        except Exception as inst:

            print("Problems with checkAttachmentChanges! Details: Exception: {} {} Issue: {}; changelog:\n fromString: {} \n toString: {} ".format(type(inst), inst.args, issueAsString, entry.fromString, entry.toString))
    return attachment_string


def checkForUpdates(historyItem):
    global assignee_included, assignee_included, attachments, assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string, attachments_included

    if webhook.postAssignee and not assignee_included:
        assignee_string, assignee_included = checkAssigneeChanges(historyItem)

    if webhook.postAttachment:
        attachments.append(checkAttachmentChanges(historyItem))
        attachments = list(filter(None, attachments))
        if len(attachments) != 0:
            attachment_string = seperator.join(attachments)
            attachments_included = True
    #
    # if webhook.postDescription:
    #     checkDescriptionChanges(historyItem)
    #
    # if webhook.postComments:
    #     checkCommentsChanges(historyItem)
    #
    # if webhook.postUXDesign:
    #     checkUXDesignChanges(historyItem)
    #
    # if webhook.postIssueType:
    #     checkIssueTypeChanges(historyItem)
    #
    # if webhook.postPriority:
    #     checkPriorityChanges(historyItem)
    return assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string, attachment_included


def init_global_vars():
    global assignee_included, attachments, assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string
    assignee_included = False
    attachments = []
    assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string = '', '', '', '', '', '', ''


if __name__ == '__main__':
    global seperator, message
    seperator = '___'
    default_avatar_url = webhook.jiraUrl + 'secure/useravatar?ownerId='
    jira = JIRA(webhook.jiraUrl, basic_auth=(webhook.username, webhook.password))
    driver = Driver({'url': webhook.url, 'scheme': webhook.scheme, 'port': webhook.port, 'verify': webhook.verify})
    lastViewed = readJSON()
    for selectedIssue in jira.search_issues(webhook.projectSearchString, maxResults=webhook.maxResults,
                                            expand=webhook.expand):
        issue = jira.issue(str(selectedIssue))
        lastViewedFormatted = formatDate(lastViewed)
        assignee, status, avatar_url = getStatusAndAssignee()
        attachment_included = False
        init_global_vars()
        if formatDate(issue.fields.updated) < lastViewedFormatted:
            issueAsString = str(issue)
            message = '' + getTitleString(getPictureString(issue.fields.priority.iconUrl, issue.fields.priority.name),
                                          issueAsString,
                                          webhook.jqlQueryString + issueAsString,
                                          str(issue.fields.summary))

            for item in (history for history in selectedIssue.changelog.histories if
                         formatDate(history.created) < lastViewedFormatted):
                for selectedItem in item.items:
                    assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string, attachment_included = checkForUpdates(selectedItem)
            if attachment_included:
                append_attachment = getAttachmentString() + attachment_string
            else:
                append_attachment = ''
            append_string = assignee_string + append_attachment + description_string + comments_string + ux_string + issueType_string + priority_string
            message = message + append_string
            print(message)
        # sendMattermost(driver, message)
    file = setTimestampJSONFile()
    writeJSON()
