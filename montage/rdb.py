# Relational database models for Montage
from sqlalchemy import (Column,
                        String,
                        Integer,
                        Float,
                        Boolean,
                        DateTime,
                        ForeignKey)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy

from sqlalchemy.ext.declarative import declarative_base

from simple_serdes import DictableBase

Base = declarative_base()

"""
Column ordering and groupings:
* ID
* Data
* Metadata (creation date)
* 1-n relationships
* n-n relationships
"""


class User(Base, DictableBase):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    last_login_date = Column(DateTime)

    create_date = Column(DateTime, server_default=func.now())

    coordinated_campaigns = relationship('CampaignCoord', back_populates='user')
    campaigns = association_proxy('coordinated_campaigns', 'campaign',
                                  creator=lambda c: CampaignCoord(campaign=c))

    jurored_rounds = relationship('RoundJuror', back_populates='user')
    rounds = association_proxy('jurored_rounds', 'round',
                               creator=lambda r: RoundJuror(round=r))
    votes = relationship('Vote', back_populates='user')
    # update_date?


class Campaign(Base, DictableBase):
    __tablename__ = 'campaigns'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    # open/close can be used to select/verify that images were
    # actually uploaded during the contest window
    open_date = Column(DateTime)
    close_date = Column(DateTime)

    create_date = Column(DateTime, server_default=func.now())

    rounds = relationship('Round', back_populates='campaign')
    campaign_coords = relationship('CampaignCoord')
    coords = association_proxy('campaign_coords', 'user',
                               creator=lambda user: CampaignCoord(coord=user))
    # round_names = association_proxy('rounds', 'name') "simplifying scalar stuff"


class CampaignCoord(Base, DictableBase):  # Coordinator, not Coordinate
    __tablename__ = 'campaign_coords'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), primary_key=True)

    user = relationship('User', back_populates='coordinated_campaigns')
    campaign = relationship('Campaign', back_populates='campaign_coords')

    def __init__(self, campaign=None, coord=None):
        if campaign is not None:
            self.campaign = campaign
        self.user = coord


class Round(Base, DictableBase):
    """The "directions" field is for coordinators to communicate
    localized directions to jurors, whereas the "description" field is
    for coordinator comments (and not shown to jurors).
    """
    __tablename__ = 'rounds'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    directions = Column(String)
    open_date = Column(DateTime)
    close_date = Column(DateTime)
    status = Column(String)
    vote_method = Column(String)
    quorum = Column(Integer)
    # Should we just have some settings in json?
    show_link = Column(Boolean)
    show_filename = Column(Boolean)
    show_resolution = Column(Boolean)

    create_date = Column(DateTime, server_default=func.now())

    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    # increments for higher rounds within the same campaign
    campaign_seq = Column(Integer, default=1)

    campaign = relationship('Campaign', back_populates='rounds')
    round_jurors = relationship('RoundJuror')
    jurors = association_proxy('round_jurors', 'user',
                               creator=lambda u: RoundJuror(user=u))
    votes = relationship('Vote', back_populates='round')
    entries = relationship('RoundEntry')


class RoundJuror(Base, DictableBase):
    __tablename__ = 'round_jurors'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), primary_key=True)

    user = relationship('User', back_populates='jurored_rounds')
    round = relationship('Round', back_populates='round_jurors')

    def __init__(self, round=None, user=None):
        if round is not None:
            # lesson setting round to None would give an error about
            # trying to "blank-out primary key column"
            self.round = round
        self.user = user


class Entry(Base, DictableBase):
    # if this is being kept generic for other types of media judging,
    # then I think a "duration" attribute makes sense -mh
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True)

    # page_id?
    name = Column(String)
    mime_major = Column(String)
    mime_minor = Column(String)
    width = Column(Integer)
    height = Column(Integer)
    resolution = Column(Integer)
    # if we ever figure out how to get the monument ID
    subject_id = Column(String)
    upload_user_id = Column(Integer)
    upload_user_text = Column(String)
    upload_date = Column(DateTime)

    # TODO: img_sha1/page_touched for updates?

    create_date = Column(DateTime, server_default=func.now())

    rounds = relationship('RoundEntry')
    """
    # I don't think we want these

    campaigns = relationship('CampaignEntry')
    votes = relationship('Vote', back_populates='entry')  # don't think we want this
    license = Column(String)
    author = Column(String)
    """


class RoundEntry(Base, DictableBase):
    __tablename__ = 'round_entries'

    entry_id = Column(Integer, ForeignKey('entries.id'), primary_key=True)
    round_id = Column(Integer, ForeignKey('rounds.id'), primary_key=True)

    entry = relationship('Entry', back_populates='rounds')
    round = relationship('Round', back_populates='entries')
    # TODO: votes?

    def __init__(self, entry=None, round=None):
        self.entry = entry
        self.round = round


class Vote(Base, DictableBase):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))
    old_task_id = Column(Integer)
    vote = Column(Float)
    is_canceled = Column(Boolean)

    create_date = Column(DateTime, server_default=func.now())

    user = relationship('User', back_populates='votes')
    round = relationship('Round', back_populates='votes')
    # entry = relationship('Entry', back_populates='votes')


class Task(Base, DictableBase):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    entry_id = Column(Integer, ForeignKey('entries.id'))
    round_id = Column(Integer, ForeignKey('rounds.id'))


class UserDAO(object):
    """The Data Acccess Object wraps the rdb_session and active user
    model, providing a layer for model manipulation through
    expressively-named methods.

    As the DAO expands, it will likely break up into multiple DAOs for
    different areas of the schema.

    # TODO: name? true that user is bound in, but UserDAO doesn't ring
    totally true.
    # TODO: will blow up a bit if user is None

    # TODO: rather than query(Model), this should do user.models and
    filter from there, I'm thinking.
    """
    def __init__(self, rdb_session, user):
        self.rdb_session = rdb_session
        self.user = user

    def query(self, *a, **kw):
        "a call-through to the underlying session.query"
        return self.rdb_session.query(*a, **kw)

    def get_campaign_config(self, campaign_id=None):
        campaign = self.query(Campaign)\
                       .filter(
                           Campaign.coords.any(username=self.user.username))\
                       .filter_by(id=campaign_id)\
                       .one()
        return campaign

    def get_campaign(self, campaign_id):
        campaign = self.query(Campaign)\
                       .filter(Campaign.rounds.any(
                           Round.jurors.any(username=self.user.username)))\
                       .filter_by(id=campaign_id)\
                       .one()
        rounds = self.query(Round)\
                     .filter(Round.jurors.any(username=self.user.username),
                             Round.campaign_id == campaign_id)\
                     .all()
        ret = campaign.to_dict()
        ret['rounds'] = [r.to_dict() for r in rounds]
        return ret

    def get_campaign_name(self, campaign_id):
        # TODO: check user permissions?
        campaign = self.query(Campaign).filter_by(id=campaign_id).one()
        return campaign.name

    def get_round_name(self, round_id):
        # TODO: check user permissions?
        round = self.query(Round).filter_by(id=round_id).one()
        return round.name

    def get_round_config(self, round_id):
        round = self.query(Round)\
                    .filter(
                        Round.campaign.has(
                            Campaign.coords.any(username=self.user.username)),
                        Round.id == round_id)\
                    .one()
        return round

    def get_round(self, round_id):
        round = self.query(Round)\
                    .filter(
                        Round.jurors.any(username=self.user.username),
                        Round.id == round_id)\
                    .one()
        return round

    def get_all_campaigns(self):
        campaigns = self.query(Campaign)\
                        .filter(
                            Campaign.coords.any(username=self.user.username))\
                        .all()
        return campaigns

    def get_all_rounds(self):
        rounds = self.query(Round)\
                     .filter(Round.jurors.any(username=self.user.username))\
                     .group_by(Round.campaign_id)\
                     .all()
        ret = [r.to_dict() for r in rounds]
        return ret


import os.path

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(os.path.dirname(CUR_PATH), 'test_data')


def make_rdb_session(db_url='sqlite:///tmp_montage.db'):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # echo="debug" also prints results of selects, etc.
    engine = create_engine(db_url, echo=True)
    Base.metadata.create_all(engine)

    session_type = sessionmaker()
    session_type.configure(bind=engine)
    session = session_type()
    return session


def make_fake_data(debug=True):
    from loaders import load_full_csv

    rdb_session = make_rdb_session()
    coord = User(username='Slaporte')
    juror = User(username='MahmoudHashemi')

    campaign = Campaign(name='Test Campaign 2016')
    rdb_session.add(campaign)

    campaign.coords.append(coord)
    round = Round(name='Test Round 1')
    campaign.rounds.append(round)
    round.jurors.append(juror)

    CSV_PATH = DATA_PATH + '/wlm2015_ir_5.csv'

    with open(CSV_PATH) as f:
        entries = load_full_csv(f)

    for entry in entries:
        rdb_session.add(entry)

    rdb_session.commit()
    if debug:
        import pdb;pdb.set_trace()
    return


def main():
    make_fake_data()
    return


if __name__ == '__main__':
    main()


"""
* Indexes
* db session management, engine creation, and schema creation separation
* prod db pw management
* add simple_serdes for E-Z APIs
"""
