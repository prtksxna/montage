from datetime import datetime

from montage.rdb import (make_rdb_session,
                         JurorDAO,
                         OrganizerDAO,
                         MaintainerDAO,
                         CoordinatorDAO,
                         lookup_user)
from montage.utils import PermissionDenied

import random

random.seed('badidea')

GIST_URL = 'https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/ca394147a841ea5f238502ffd07cbba54b9b1a6a/wlm2015_fr_500.csv'


def cross_complete(rdb_session, rnd):
    juror1, juror2 = rnd.jurors[0], rnd.jurors[1]
    juror1_dao = JurorDAO(rdb_session, juror1)
    task = juror1_dao.get_tasks_from_round(rnd, num=1)[0]

    juror2_dao = JurorDAO(rdb_session, juror2)
    juror2_dao.apply_rating(task, 0.2)

    return


def rate_round_tasks(rdb_session, rnd, limit_per=None):
    for juror in rnd.jurors:
        print '.. voting for %s' % juror.username
        juror_dao = JurorDAO(rdb_session, juror)
        tasks = juror_dao.get_tasks_from_round(rnd)

        count = 0
        while tasks:
            if limit_per and count > limit_per:
                break
            task = tasks.pop()
            vote = random.choice([0.0, 0.25, 0.5, 0.75, 1.0])
            juror_dao.apply_rating(task, vote)
            tasks = juror_dao.get_tasks_from_round(rnd)
            count += 1

    return


def main():
    rdb_session = make_rdb_session()

    cur_user = 'MahmoudHashemi'  # maintainer
    user_obj = lookup_user(rdb_session, cur_user)

    maint_dao = MaintainerDAO(rdb_session, user_obj)
    maint_dao.add_organizer('LilyOfTheWest')

    org_user = lookup_user(rdb_session, 'LilyOfTheWest')
    org_dao = OrganizerDAO(rdb_session, org_user)

    # should automatically add the creator as coordinator
    campaign = org_dao.create_campaign(name='Test Campaign 2016',
                                       open_date=datetime(2015, 9, 10),
                                       close_date=datetime(2015, 10,1))

    org_dao.add_coordinator(campaign, username='Yarl')
    org_dao.add_coordinator(campaign, 'Slaporte')

    coord_user = lookup_user(rdb_session, 'Yarl')
    coord_dao = CoordinatorDAO(rdb_session, coord_user)

    rnd = coord_dao.create_round(name='Test Round 1',
                                 quorum=3,
                                 vote_method='rating',
                                 jurors=['Slaporte', 'MahmoudHashemi', 'Yarl'],
                                 campaign=campaign)
    # returns successful, disqualified, total counts
    # coord_dao.add_entries_from_cat(rnd, 'Wiki Loves Monuments France 2015')

    coord_dao.add_entries_from_csv_gist(rnd, GIST_URL)

    coord_dao.autodisqualify_by_date(rnd)
    coord_dao.autodisqualify_by_resolution(rnd)

    #coord_dao.disqualify_entry(entry)

    coord_dao.activate_round(rnd)

    try:
        cross_complete(rdb_session, rnd)
    except PermissionDenied:
        pass
    else:
        raise ValueError('expected permission denied on cross complete')

    rate_round_tasks(rdb_session, rnd, limit_per=20)

    coord_dao.cancel_round(rnd)

    # # should fail, quorum must be <= # of jurors
    # coord_dao.reassign(active_jurors=['Slaporte'])

    rnd = coord_dao.create_round(name='Test Round 2',
                                 quorum=3,
                                 vote_method='rating',
                                 jurors=['Slaporte', 'MahmoudHashemi', 'Yarl'],
                                 campaign=campaign)
    coord_dao.add_entries_from_csv_gist(rnd, GIST_URL)
    coord_dao.activate_round(rnd)

    rate_round_tasks(rdb_session, rnd, limit_per=20)

    # some read tasks

    rate_round_tasks(rdb_session, rnd)

    ratings_res = coord_dao.get_round_average_ratings(rnd)

    # coord_dao.finalize_round(rnd)

    # coord_dao.reassign(active_jurors=['Slaporte', 'Yarl'])

    # # a loop going over a bunch more ratings probably until
    # # get_next_task returns None

    # # coord_dao can do the following, too
    # # org_dao.cancel_round
    # org_dao.close_round(rnd)

    # # start new round
    # # close round
    # # close campaign
    # # download audit logs

    rdb_session.commit()
    import pdb;pdb.set_trace()


if __name__ == '__main__':
    main()
