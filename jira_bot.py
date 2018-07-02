import sys
from mattermostdriver import Driver
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
                   '\s+\*(\w+)\*\s+': '**\\1**',
                   '\s+-(\w+)-\s+': '~~\\1~~',
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
                   '(\![\w\-_\.äüö]+\.\w+\!)': '\\1',
                   '!([\w\s\-_\+]*\.\w+)\|thumbnail!': '\\1',
                   '!([\w\s\-_\+]*\.\w+)!': '\\1'}
    return adjust_dict


def getCommentString():
    return ' \n{} **@{}**: \n {} \n\n Erstellt: {} \n Updated: {} \n\n'


def getCommentHeadline():
    return ' \n #### Kommentare:'


def getAttachmentString():
    return '\n #### Folgende Anhänge wurden hinzugefügt: \n'


def getStatusString(status):
    return '\n #### Status: {} \n'.format(status)


def getAssigneeString(current_avatar_link, current_username):
    return '\n #### Bearbeiter: {} @{} \n'.format(current_avatar_link, current_username)


def getAssigneeChangedString(old_avatar_link, old_username, new_avatar_link, new_username):
    return '\n #### Bearbeiter: von {} @{} zu {} @{} \n'.format(old_avatar_link, old_username, new_avatar_link,
                                                                new_username)


def getDescriptionChangedString(description):
    return '\n #### Beschreibung (verändert): \n {} \n'.format(description)


def getUXDesignChangedString(link):
    return '\n Folgendes UX Design wurde hinzugefügt: [click here]({})'.format(link)


def changeString(field, old, new):
    return '\n #### {}: von ~~{}~~ zu {} \n'.format(field, old, new)


def getTitleString(picture, issue_as_string, link_to_issue, summary):
    return '### {} [{}]({}): {} \n'.format(picture, issue_as_string, link_to_issue, summary)


def getPictureString(link_to_pic, hover_text):
    return '![Jira]({} =30x30 "{}")'.format(link_to_pic, hover_text)


def getPictureStringWithLink(link_to_pic, hover_text):
    return '\n [![{}]({} "{}")]({}) \n'.format(hover_text, link_to_pic, hover_text, link_to_pic)


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


def getStatusAndAssignee(issue):
    status = issue.fields.status.name
    if issue.fields.assignee is not None:
        assignee = issue.fields.assignee.key
    else:
        assignee = 'unlocated'
    return assignee, status


def setTimestampJSONFile():
    file = {
        "timestamp": getTimestamp(),
    }
    return file


def readJSON():
    try:
        with open(webhook.pathToFile, "r") as read_file:
            lastViewed = json.load(read_file)
        lastViewed = lastViewed["timestamp"]
        return lastViewed
    except Exception as inst:
        print(inst.args)


def writeJSON():
    try:
        with open(webhook.pathToFile, "w") as write_file:
            print("file = {}".format(str(file)))
            json.dump(file, write_file)
    except Exception as inst:
        print(inst.args)


def print_exception_details(entry, inst, issue_as_string):
    print("Problems with {}! Details: Exception: {} {} Issue: {}; changelog:\n fromString: {} \n toString: {} ".format(
        'checkAttachmentChanges', type(inst), inst.args, issue_as_string, entry.fromString, entry.toString))


def checkNewComments(issue, last_viewed_formatted):
    global comments_string
    if len(issue.fields.comment.comments) > 0:
        gen = (comment for comment in issue.fields.comment.comments if
               formatDate(comment.updated) > last_viewed_formatted)
        all_comments = [
            (comment.author.name, comment.body, comment.created, comment.updated)
            for comment in gen]
        comments_selected = [
            getCommentString().format(getPictureString(default_avatar_url + author, author), author, adjustSyntax(body),
                                      formatDate(created),
                                      formatDate(updated))
            for (author, body, created, updated) in all_comments]

        if len(comments_selected) > 0:
            comments_string = seperator.join(comments_selected)
    return comments_string


def checkStatusChanges(entry, new_status, issue_as_string):
    global status_string
    status_mentioned = False
    if entry.field == 'status' and not status_mentioned:
        try:
            if entry.fromString is not None:
                old_status = entry.fromString
                status_string = changeString('Status', old_status, new_status)
                status_mentioned = True
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    elif not status_mentioned:
        status_string = getStatusString(new_status)
    return status_string, status_mentioned


def checkAssigneeChanges(entry, assignee, issue_as_string):
    global assignee_string
    assignee_mentioned = False
    if entry.field == 'assignee' and not assignee_mentioned:
        try:
            if entry.fromString is not None:
                oldAssignee = jira.search_users(entry.fromString)[0].key
                assignee_string = getAssigneeChangedString(
                    getPictureString(default_avatar_url + oldAssignee, oldAssignee),
                    oldAssignee,
                    getPictureString(default_avatar_url + assignee, assignee),
                    assignee)

                assignee_mentioned = True
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    elif not assignee_mentioned:
        assignee_string = create_default_assignee_string(assignee)
    return assignee_string, assignee_mentioned


def checkAttachmentChanges(entry, issue_as_string):
    global attachment_string, attachments, attachment_included
    if entry.field == 'Attachment':
        try:
            pictureString, pictureURL = get_attachment_data(entry)
            attachment_string = getPictureStringWithLink(pictureURL, pictureString)
            attachments.append(attachment_string)
            attachments = list(filter(None, attachments))
            if len(attachments) > 0:
                attachment_string = seperator.join(attachments)
                attachment_included = True
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    return attachment_string, attachment_included


def get_attachment_data(entry):
    pictureString = entry.toString
    pictureID = entry.to
    if pictureID is not None:
        attachmentObject = jira.attachment(pictureID)
        pictureURL = attachmentObject.content
        return pictureString, pictureURL


def checkDescriptionChanges(entry, issue_as_string, issue):
    global description_string
    if entry.field == 'description':
        try:
            newDescription = adjustSyntax(issue.fields.description)
            description_string = getDescriptionChangedString(newDescription)
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    return description_string


def checkUXDesignChanges(entry, issue_as_string):
    global ux_string
    if entry.field == 'UX Design':
        try:
            newUXDesign_link = entry.toString
            ux_string = getUXDesignChangedString(newUXDesign_link)
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    return ux_string


def checkIssueTypeChanges(entry, issue_as_string):
    global issueType_string
    if entry.field == 'issuetype':
        try:
            old_type, new_type = get_changes(entry)
            issueType_string = changeString('Ticket-Typ', old_type, new_type)
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    return issueType_string


def checkPriorityChanges(entry, issue_as_string):
    global priority_string
    if entry.field == 'priority':
        try:
            old_priority, new_priority = get_changes(entry)
            priority_string = changeString('Priorität', old_priority, new_priority)
        except Exception as inst:
            print_exception_details(entry, inst, issue_as_string)
    return priority_string


def get_changes(entry):
    return entry.fromString, entry.toString


def checkForUpdates(historyItem, assignee, status, issue_as_string, issue):
    global status_included, assignee_included, attachment_included, attachments, status_string, assignee_string, attachment_string, description_string, ux_string, issueType_string, priority_string

    if webhook.postStatus and not status_included:
        status_string, status_included = checkStatusChanges(historyItem, status, issue_as_string)

    if webhook.postAssignee and not assignee_included:
        assignee_string, assignee_included = checkAssigneeChanges(historyItem, assignee, issue_as_string)

    if webhook.postAttachment:
        attachment_string, attachment_included = checkAttachmentChanges(historyItem, issue_as_string)

    if webhook.postDescription:
        description_string = checkDescriptionChanges(historyItem, issue_as_string, issue)

    if webhook.postUXDesign:
        ux_string = checkUXDesignChanges(historyItem, issue_as_string)

    if webhook.postIssueType:
        issueType_string = checkIssueTypeChanges(historyItem, issue_as_string)

    if webhook.postPriority:
        checkPriorityChanges(historyItem, issue_as_string)

    return status_string, assignee_string, attachment_string, description_string, ux_string, issueType_string, priority_string, attachment_included


def init_global_vars():
    global seperator, message, status_included, assignee_included, attachment_included, attachments, all_attachments, status_string, assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string
    seperator = '___'


def init_jira():
    jira = JIRA(webhook.jiraUrl, basic_auth=(webhook.username, webhook.password))
    return jira


def init_mattermost_driver():
    driver = Driver({'url': webhook.url, 'scheme': webhook.scheme, 'port': webhook.port, 'verify': webhook.verify})
    return driver


def iterate_through_issues():
    global message, status_string, assignee_string, attachment_string, description_string, ux_string, issueType_string, priority_string, attachment_included, comments_string, status_included, assignee_included, attachments, all_attachments
    for selectedIssue in jira.search_issues(webhook.projectSearchString, maxResults=webhook.maxResults,
                                            expand=webhook.expand):
        issue = jira.issue(str(selectedIssue))
        last_viewed_formatted = formatDate(lastViewed)
        assignee, status = getStatusAndAssignee(issue)
        if formatDate(issue.fields.updated) > last_viewed_formatted:
            issue_as_string = str(issue)
            reset_variables()
            priority_picture = getPictureString(issue.fields.priority.iconUrl, issue.fields.priority.name)
            issue_link = webhook.jqlQueryString + issue_as_string
            init_message_with_title(issue, issue_as_string, issue_link, priority_picture)
            all_attachments = collect_all_attachments(issue_as_string, selectedIssue)
            iterate_through_changelog(assignee, issue_as_string, last_viewed_formatted, selectedIssue, status, issue)
            description_string = link_attachments(all_attachments, description_string)
            append_string = construct_append_string(assignee_string, attachment_included, attachment_string,
                                                    description_string, issue, issueType_string, last_viewed_formatted,
                                                    priority_string, status_string, ux_string, status_included, assignee_included, assignee, status)
            message = message + append_string
            sendMattermost(driver, message)


def link_attachments(all_attachments, text):
    for attachment in all_attachments:
        try:
            attachment_split = attachment.split("|")
            picture_string = attachment_split[0]
            picture_url = attachment_split[1]
            text = re.compile(picture_string).sub("[![{}]({})]({})".format(picture_string, picture_url, picture_url), text)
        except Exception as inst:
            print(inst.args)
    return text


def collect_all_attachments(issue_as_string, selectedIssue):
    global all_attachments
    all_attachments = []
    for item in (history for history in selectedIssue.changelog.histories):
        for entry in item.items:
            if entry.field == 'Attachment':
                try:
                    if entry.to is not None:
                        pictureString, pictureURL = get_attachment_data(entry)
                        all_attachments.append("{}|{}".format(pictureString, pictureURL))
                except Exception as inst:
                    print_exception_details(entry, inst, issue_as_string)
    return all_attachments

def construct_append_string(assignee_string, attachment_included, attachment_string, description_string, issue,
                            issueType_string, last_viewed_formatted, priority_string, status_string, ux_string, status_included, assignee_included, assignee, status):
    global comments_string
    if webhook.postComments:
        comments_string = checkNewComments(issue, last_viewed_formatted)
        if comments_string != '':
            comments_string = getCommentHeadline() + comments_string
    if attachment_included:
        append_attachment = getAttachmentString() + attachment_string
    else:
        append_attachment = ''
    if not status_included:
        status_string = getStatusString(status)
    if not assignee_included:
        assignee_string = create_default_assignee_string(assignee)
    append_string = priority_string + issueType_string + status_string + assignee_string + ux_string + description_string + comments_string + append_attachment
    return append_string


def create_default_assignee_string(assignee):
    assignee_string = getAssigneeString(getPictureString(default_avatar_url + assignee, assignee), assignee)
    return assignee_string


def iterate_through_changelog(assignee, issue_as_string, last_viewed_formatted, selectedIssue, status, issue):
    global status_string, assignee_string, attachment_string, description_string, ux_string, issueType_string, priority_string, attachment_included
    for item in (history for history in selectedIssue.changelog.histories if
                 formatDate(history.created) > last_viewed_formatted):
        for selectedItem in item.items:
            status_string, assignee_string, attachment_string, description_string, ux_string, issueType_string, priority_string, attachment_included = checkForUpdates(
                selectedItem, assignee, status, issue_as_string, issue)


def init_message_with_title(issue, issue_as_string, issue_link, priority_picture):
    global message
    message = '' + getTitleString(priority_picture,
                                  issue_as_string,
                                  issue_link,
                                  str(issue.fields.summary))


def reset_variables():
    global status_string, assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string, status_included, assignee_included, attachment_included, attachments, all_attachments
    status_string, assignee_string, attachment_string, description_string, comments_string, ux_string, issueType_string, priority_string = '', '', '', '', '', '', '', ''
    status_included = False
    assignee_included = False
    attachment_included = False
    attachments = []
    all_attachments = []


if __name__ == '__main__':
    init_global_vars()
    default_avatar_url = webhook.jiraUrl + 'secure/useravatar?ownerId='
    jira = init_jira()
    driver = init_mattermost_driver()
    lastViewed = readJSON()
    iterate_through_issues()
    file = setTimestampJSONFile()
    writeJSON()
