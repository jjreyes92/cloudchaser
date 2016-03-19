import sys
import soundcloud
import networkx as nx
from py2neo import Graph
from requests.exceptions import ConnectionError, HTTPError
from utils import get_results, handle_http_errors

client = soundcloud.Client(client_id='454aeaee30d3533d6d8f448556b50f23')

id2username_cache = {}
artistGraph = Graph()

@handle_http_errors
def id2username(profile, kind='users'):
    global id2username_dict
    username = id2username_cache.get(profile, None)
    if username is not None: return username

    # username is none, we don't have it in cache
    result = client.get('/%s/%s' % (kind, str(profile)))
    if kind == 'comments':
        username = result.user['username']
    elif kind == 'tracks':
        username = result.title
    else:
        username = result.username
    # encode it correctly
    username = str(username.encode('utf-8'))
    id2username_cache[profile] = username
    return username

@handle_http_errors
def getFollowings(profile):
    # get list of users who the artist is following.
    followings = get_results(client, '/users/{0:s}/followings/'.format(str(profile)))
    return followings

@handle_http_errors
def getFollowers(profile):
    followers = get_results(client, '/users/{0:s}/followers/'.format(str(profile)))
    return followers

@handle_http_errors
def getFavorites(profile):
    favorites = get_results(client, '/users/{0:s}/favorites/'.format(str(profile)))
    return favorites

@handle_http_errors
def getComments(profile):
    comments = get_results(client, '/users/{0:s}/comments/'.format(str(profile)))
    return [comment.user['id'] for comment in comments]

@handle_http_errors
def getTracks(profile):
    tracks = get_results(client, '/users/{0:s}/tracks/'.format(str(profile)))
    return [track.id for track in tracks]

def getWeight(profile, neighbor, artistNet, attr):
        if artistNet.has_edge(profile, neighbor, key=attr):
                return artistNet.get_edge_data(profile, neighbor, key=attr)['weight'] + 1
        else:
          return 1

def addWeight(profile, neighbor, artistNet, attr):
    new_weight = getWeight(profile, neighbor, artistNet, attr)
    artistNet.add_edge(profile, neighbor, key=attr, weight=new_weight)
    print "\t", "%s --> %s" % (id2username(profile), id2username(neighbor))
    return new_weight

def addAction(action, profile, neighbor, weight):
    query = '(profile {username: {username} } ) - [interaction : {action} { weight: [ {weight} ] } ] -> (neighbor {username: {neighbor} } )'
    artistGraph.cypher.execute(query, {'username': id2username(profile), 'action': action, 'neighbor': id2username(neighbor), 'weight': weight})

def addFollowings(artist, followings, artistNet):
    print "Adding followings for %s" % (id2username(artist))
    for user in followings:
        addAction(follows, artist, user, addWeight(artist, user, artistNet, 'fol_weight'))

def addFollowers(artist, followers, artistNet):
    print "Adding followers for %s" % (id2username(artist))
    for user in followers:
        addAction(follows, user, artist, addWeight(user, artist, artistNet, 'fol_weight'))

def addFavorites(artist, favorites, artistNet):
    print "Adding favorites for %s" % (id2username(artist))
    for user in favorites:
        addAction(favorites, artist, user, addWeight(artist, user, artistNet, 'fav_weight'))

def addComments(artist, comments, artistNet):
    print "Adding comments for %s" % (id2username(artist))
    for user in comments:
        addAction(comments, artist, user, addWeight(artist, user, artistNet, 'com_weight'))

def addTracks(artist, tracks, artistNet):
    for track in tracks:
    # get list of users who have favorited this user's track
        favoriters = get_results(client, '/tracks/' + str(track) + '/favoriters')
        print "Adding favoriters for %s" % (id2username(artist))
        for user in favoriters:
            addAction(favorites, user.id, artist, addWeight(user.id, artist, artistNet, 'fav_weight'))

    # get list of users who have commented on this user's track
        commenters = get_results(client, '/tracks/' + str(track) + '/comments')
        print "Adding commenters for %s" % (id2username(artist))
        for comment in commenters:
            addAction(comments, comment.user['id'], artist, addWeight(comment.user['id'], artist, artistNet, 'com_weight'))
