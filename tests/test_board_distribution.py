import tempfile,unittest
from pathlib import Path
from poker_evaluator.board_distribution import evaluate_board_distribution
from poker_evaluator.relative_strength import evaluate_relative_strength
from poker_evaluator.storage import Repository

class DistributionTests(unittest.TestCase):
    def test_weighted_turn_mean_matches_joint_exact(self):
        from poker_evaluator.range_parser import HandCombo
        from poker_evaluator.cards import parse_card
        from poker_evaluator.multiway.deal_distribution import WeightedRange
        def hand(s): return HandCombo(*(parse_card(x) for x in s.split()))
        pool=WeightedRange(((hand('Kc Kh'),3),(hand('Qc Qh'),1)))
        kw=dict(hero='As Ah',board='Ks 8h 7d 3c')
        result=evaluate_board_distribution(**kw,opponent=pool)
        exact=evaluate_relative_strength(**kw,opponent_ranges=[pool],mode='exact')
        self.assertAlmostEqual(result.mean,exact.equity,places=12)
        self.assertEqual(result.boards,46)
        self.assertAlmostEqual(sum(result.histogram),1)
        self.assertLessEqual(result.quantiles['0.1'],result.quantiles['0.5'])
        self.assertLessEqual(result.quantiles['0.5'],result.quantiles['0.9'])
    def test_river_one_board_and_tie(self):
        d=evaluate_board_distribution('2c 3d','As Ks Qs Js Ts','44')
        self.assertEqual(d.boards,1);self.assertAlmostEqual(d.mean,.5);self.assertEqual(d.variance,0)
    def test_invalid_and_limit(self):
        with self.assertRaises(ValueError):evaluate_board_distribution('As Ah','','KK')
        with self.assertRaises(ValueError):evaluate_board_distribution('As Ah','Ks 8h 7d','random',max_candidates=10)
    def test_existing_v1_database_migrates_without_losing_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'db.sqlite'; repo=Repository(path)
            session=repo.create_session('kept')
            with repo.connect() as conn:
                conn.execute('DROP TABLE research_results')
                conn.execute('PRAGMA user_version=1')
            migrated=Repository(path)
            self.assertEqual(migrated.sessions()[0]['id'],session)
            migrated.save_research_result(session,'board_distribution',{'mean':.5})
            self.assertEqual(len(migrated.research_results(session)),1)

    def test_db_round_trip_and_session_isolation(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'db.sqlite';repo=Repository(p)
            first=repo.create_session('a');second=repo.create_session('b')
            repo.save_research_result(first,'board_distribution',{'conditions':{'hero':['As','Ah']},'mean':.5})
            self.assertEqual(len(Repository(p).research_results(first)),1)
            self.assertEqual(repo.research_results(second),[])
            import json
            self.assertEqual(json.loads(repo.research_results(first)[0]['result_json'])['mean'],.5)

if __name__=='__main__':unittest.main()

