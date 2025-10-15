#!/usr/bin/env python3
"""
LeekWars Fight Database Manager
SQLite database for tracking fight history and opponent statistics
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class FightDatabase:
    """Manages fight history database for a specific leek"""

    def __init__(self, leek_id: int):
        """
        Initialize database for a specific leek

        Args:
            leek_id: The LeekWars leek ID
        """
        self.leek_id = leek_id
        self.db_file = f"fight_history_{leek_id}.db"
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_schema()
        self._ensure_leek_exists()

    def _connect(self):
        """Connect to the SQLite database"""
        self.conn = sqlite3.connect(self.db_file)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.cursor = self.conn.cursor()

    def _create_schema(self):
        """Create database schema if it doesn't exist"""
        # Leeks table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS leeks (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Opponents table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS opponents (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Fights table (detailed history)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fight_id INTEGER UNIQUE NOT NULL,
                leek_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                result TEXT NOT NULL CHECK(result IN ('WIN', 'LOSS', 'DRAW')),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration INTEGER,
                actions_count INTEGER,
                fight_url TEXT,
                FOREIGN KEY(leek_id) REFERENCES leeks(id),
                FOREIGN KEY(opponent_id) REFERENCES opponents(id)
            )
        ''')

        # Opponent stats table (aggregate statistics)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS opponent_stats (
                leek_id INTEGER NOT NULL,
                opponent_id INTEGER NOT NULL,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                total_fights INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                status TEXT DEFAULT 'unknown' CHECK(status IN ('beatable', 'dangerous', 'even', 'unknown')),
                first_fought TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_fought TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(leek_id, opponent_id),
                FOREIGN KEY(leek_id) REFERENCES leeks(id),
                FOREIGN KEY(opponent_id) REFERENCES opponents(id)
            )
        ''')

        # Create indexes for better query performance
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_fights_leek_opponent
            ON fights(leek_id, opponent_id)
        ''')

        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_fights_timestamp
            ON fights(timestamp DESC)
        ''')

        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_opponent_stats_status
            ON opponent_stats(leek_id, status)
        ''')

        self.conn.commit()

    def _ensure_leek_exists(self):
        """Ensure the current leek exists in the database"""
        self.cursor.execute('SELECT id FROM leeks WHERE id = ?', (self.leek_id,))
        if not self.cursor.fetchone():
            self.cursor.execute('''
                INSERT INTO leeks (id, name, level)
                VALUES (?, ?, ?)
            ''', (self.leek_id, f"Leek_{self.leek_id}", 1))
            self.conn.commit()

    def update_leek_info(self, name: str, level: int):
        """Update leek information"""
        self.cursor.execute('''
            UPDATE leeks
            SET name = ?, level = ?, last_updated = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (name, level, self.leek_id))
        self.conn.commit()

    def update_opponent_info(self, opponent_id: int, name: str, level: int):
        """Update or insert opponent information"""
        self.cursor.execute('SELECT id FROM opponents WHERE id = ?', (opponent_id,))
        if self.cursor.fetchone():
            self.cursor.execute('''
                UPDATE opponents
                SET name = ?, level = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, level, opponent_id))
        else:
            self.cursor.execute('''
                INSERT INTO opponents (id, name, level)
                VALUES (?, ?, ?)
            ''', (opponent_id, name, level))
        self.conn.commit()

    def record_fight(self, fight_data: Dict) -> bool:
        """
        Record a fight in the database

        Args:
            fight_data: Dict containing:
                - fight_id: int
                - opponent_id: int
                - opponent_name: str
                - opponent_level: int (optional)
                - result: str (WIN/LOSS/DRAW)
                - duration: int (optional)
                - actions_count: int (optional)
                - fight_url: str (optional)

        Returns:
            True if fight was recorded successfully, False if already exists
        """
        fight_id = fight_data['fight_id']
        opponent_id = fight_data['opponent_id']
        opponent_name = fight_data['opponent_name']
        opponent_level = fight_data.get('opponent_level', 1)
        result = fight_data['result']
        duration = fight_data.get('duration')
        actions_count = fight_data.get('actions_count')
        fight_url = fight_data.get('fight_url', f"https://leekwars.com/fight/{fight_id}")

        # Update opponent info
        self.update_opponent_info(opponent_id, opponent_name, opponent_level)

        # Check if fight already exists
        self.cursor.execute('SELECT id FROM fights WHERE fight_id = ?', (fight_id,))
        if self.cursor.fetchone():
            return False  # Fight already recorded

        # Insert fight record
        self.cursor.execute('''
            INSERT INTO fights (fight_id, leek_id, opponent_id, result, duration, actions_count, fight_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (fight_id, self.leek_id, opponent_id, result, duration, actions_count, fight_url))

        # Update opponent stats
        self._update_opponent_stats(opponent_id, result)

        self.conn.commit()
        return True

    def _update_opponent_stats(self, opponent_id: int, result: str):
        """Update aggregate statistics for an opponent"""
        # Get current stats or create new record
        self.cursor.execute('''
            SELECT wins, losses, draws, total_fights
            FROM opponent_stats
            WHERE leek_id = ? AND opponent_id = ?
        ''', (self.leek_id, opponent_id))

        row = self.cursor.fetchone()
        if row:
            wins, losses, draws, total_fights = row
        else:
            wins, losses, draws, total_fights = 0, 0, 0, 0

        # Update counts
        if result == 'WIN':
            wins += 1
        elif result == 'LOSS':
            losses += 1
        elif result == 'DRAW':
            draws += 1

        total_fights += 1
        win_rate = wins / total_fights if total_fights > 0 else 0.0

        # Determine status
        status = 'unknown'
        if total_fights >= 2:
            if wins >= 2 and win_rate >= 0.7:
                status = 'beatable'
            elif losses >= 2 and win_rate <= 0.3:
                status = 'dangerous'
            else:
                status = 'even'

        # Upsert stats
        if row:
            self.cursor.execute('''
                UPDATE opponent_stats
                SET wins = ?, losses = ?, draws = ?, total_fights = ?,
                    win_rate = ?, status = ?, last_fought = CURRENT_TIMESTAMP
                WHERE leek_id = ? AND opponent_id = ?
            ''', (wins, losses, draws, total_fights, win_rate, status, self.leek_id, opponent_id))
        else:
            self.cursor.execute('''
                INSERT INTO opponent_stats
                (leek_id, opponent_id, wins, losses, draws, total_fights, win_rate, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.leek_id, opponent_id, wins, losses, draws, total_fights, win_rate, status))

    def get_opponent_stats(self, opponent_id: int) -> Optional[Dict]:
        """Get statistics for a specific opponent"""
        self.cursor.execute('''
            SELECT os.*, o.name, o.level
            FROM opponent_stats os
            JOIN opponents o ON os.opponent_id = o.id
            WHERE os.leek_id = ? AND os.opponent_id = ?
        ''', (self.leek_id, opponent_id))

        row = self.cursor.fetchone()
        if row:
            return dict(row)
        return None

    def get_all_opponent_stats(self, status: Optional[str] = None) -> List[Dict]:
        """
        Get statistics for all opponents

        Args:
            status: Filter by status ('beatable', 'dangerous', 'even', 'unknown')

        Returns:
            List of opponent stat dictionaries
        """
        if status:
            self.cursor.execute('''
                SELECT os.*, o.name, o.level
                FROM opponent_stats os
                JOIN opponents o ON os.opponent_id = o.id
                WHERE os.leek_id = ? AND os.status = ?
                ORDER BY os.win_rate DESC, os.total_fights DESC
            ''', (self.leek_id, status))
        else:
            self.cursor.execute('''
                SELECT os.*, o.name, o.level
                FROM opponent_stats os
                JOIN opponents o ON os.opponent_id = o.id
                WHERE os.leek_id = ?
                ORDER BY os.win_rate DESC, os.total_fights DESC
            ''', (self.leek_id,))

        return [dict(row) for row in self.cursor.fetchall()]

    def get_global_stats(self) -> Dict:
        """Get overall statistics"""
        self.cursor.execute('''
            SELECT
                COUNT(*) as total_fights,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN result = 'DRAW' THEN 1 ELSE 0 END) as draws
            FROM fights
            WHERE leek_id = ?
        ''', (self.leek_id,))

        row = self.cursor.fetchone()
        total_fights = row['total_fights'] or 0
        wins = row['wins'] or 0
        losses = row['losses'] or 0
        draws = row['draws'] or 0

        self.cursor.execute('''
            SELECT
                SUM(CASE WHEN status = 'beatable' THEN 1 ELSE 0 END) as beatable,
                SUM(CASE WHEN status = 'dangerous' THEN 1 ELSE 0 END) as dangerous,
                COUNT(*) as opponents_tracked
            FROM opponent_stats
            WHERE leek_id = ?
        ''', (self.leek_id,))

        row2 = self.cursor.fetchone()

        return {
            'total_fights': total_fights,
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'win_rate': wins / total_fights if total_fights > 0 else 0.0,
            'opponents_tracked': row2['opponents_tracked'] or 0,
            'beatable_opponents': row2['beatable'] or 0,
            'dangerous_opponents': row2['dangerous'] or 0
        }

    def get_win_rate_trend(self, opponent_id: int, last_n: int = 10) -> Dict:
        """
        Get win rate trend for recent fights against an opponent

        Args:
            opponent_id: Opponent ID
            last_n: Number of recent fights to analyze

        Returns:
            Dict with trend data
        """
        self.cursor.execute('''
            SELECT result, timestamp
            FROM fights
            WHERE leek_id = ? AND opponent_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (self.leek_id, opponent_id, last_n))

        fights = self.cursor.fetchall()
        if not fights:
            return {'recent_fights': 0, 'recent_win_rate': 0.0, 'trending': 'unknown'}

        wins = sum(1 for f in fights if f['result'] == 'WIN')
        recent_win_rate = wins / len(fights)

        # Compare to overall win rate
        overall_stats = self.get_opponent_stats(opponent_id)
        if overall_stats:
            overall_win_rate = overall_stats['win_rate']
            if recent_win_rate > overall_win_rate + 0.2:
                trending = 'improving'
            elif recent_win_rate < overall_win_rate - 0.2:
                trending = 'declining'
            else:
                trending = 'stable'
        else:
            trending = 'unknown'

        return {
            'recent_fights': len(fights),
            'recent_win_rate': recent_win_rate,
            'trending': trending,
            'results': [f['result'] for f in reversed(fights)]  # Chronological order
        }

    def calculate_opponent_difficulty(self, opponent_id: int) -> int:
        """
        Calculate opponent difficulty rating (0-100)
        Higher = more difficult

        Args:
            opponent_id: Opponent ID

        Returns:
            Difficulty rating (0-100)
        """
        stats = self.get_opponent_stats(opponent_id)
        if not stats:
            return 50  # Unknown = medium difficulty

        win_rate = stats['win_rate']
        total_fights = stats['total_fights']

        # Base difficulty from loss rate
        base_difficulty = (1 - win_rate) * 100

        # Confidence multiplier (more fights = more confident)
        confidence = min(total_fights / 10, 1.0)  # Max confidence at 10 fights

        # Check recent trend
        trend = self.get_win_rate_trend(opponent_id, last_n=5)
        trend_modifier = 0
        if trend['trending'] == 'declining':
            trend_modifier = 10  # Getting harder
        elif trend['trending'] == 'improving':
            trend_modifier = -10  # Getting easier

        difficulty = base_difficulty * confidence + (1 - confidence) * 50 + trend_modifier
        return max(0, min(100, int(difficulty)))

    def get_preferred_opponents(self, available_opponents: List[Dict], strategy: str = 'smart') -> List[Dict]:
        """
        Filter and rank opponents based on strategy

        Args:
            available_opponents: List of dicts with 'id', 'name', 'level' keys
            strategy: Selection strategy

        Returns:
            Filtered and ranked list of opponents
        """
        if strategy == 'random':
            return available_opponents

        # Annotate opponents with stats
        annotated = []
        for opp in available_opponents:
            opp_id = opp['id']
            stats = self.get_opponent_stats(opp_id)

            if stats:
                difficulty = self.calculate_opponent_difficulty(opp_id)
                annotated.append({
                    'opponent': opp,
                    'stats': stats,
                    'difficulty': difficulty,
                    'confidence': min(stats['total_fights'] / 10, 1.0)
                })
            else:
                # Unknown opponent
                annotated.append({
                    'opponent': opp,
                    'stats': None,
                    'difficulty': 50,  # Neutral
                    'confidence': 0.0
                })

        # Strategy-specific filtering and sorting
        if strategy == 'safe':
            # Exclude dangerous, prefer low difficulty
            filtered = [a for a in annotated if not (a['stats'] and a['stats']['status'] == 'dangerous')]
            filtered.sort(key=lambda x: x['difficulty'])

        elif strategy == 'smart':
            # Prefer beatable > unknown > avoid worst dangerous
            beatable = [a for a in annotated if a['stats'] and a['stats']['status'] == 'beatable']
            unknown = [a for a in annotated if not a['stats'] or a['stats']['status'] == 'unknown']
            even = [a for a in annotated if a['stats'] and a['stats']['status'] == 'even']
            risky = [a for a in annotated if a['stats'] and a['stats']['status'] == 'dangerous']

            beatable.sort(key=lambda x: -x['stats']['win_rate'])  # Best first
            unknown.sort(key=lambda x: x['difficulty'])
            risky.sort(key=lambda x: x['difficulty'])

            # Include some risky for variety (top 2 least difficult)
            filtered = beatable + unknown + even + risky[:2]

        elif strategy == 'aggressive':
            # Include all, prefer easier first
            filtered = annotated
            filtered.sort(key=lambda x: x['difficulty'])

        elif strategy == 'adaptive':
            # Prefer improving trends and high confidence matchups
            for a in annotated:
                if a['stats']:
                    trend = self.get_win_rate_trend(a['opponent']['id'], last_n=5)
                    a['trend_score'] = 10 if trend['trending'] == 'improving' else (-10 if trend['trending'] == 'declining' else 0)
                else:
                    a['trend_score'] = 0

            filtered = annotated
            # Sort by: confidence * win_rate + trend_score
            filtered.sort(key=lambda x: -(x['confidence'] * (1 - x['difficulty']/100) + x['trend_score']/20))

        elif strategy == 'confident':
            # Only fight opponents we have high confidence in
            filtered = [a for a in annotated if a['confidence'] >= 0.5]
            filtered.sort(key=lambda x: x['difficulty'])

        else:
            filtered = annotated

        return [a['opponent'] for a in filtered] if filtered else available_opponents

    def get_recent_fights(self, limit: int = 20) -> List[Dict]:
        """Get recent fight history"""
        self.cursor.execute('''
            SELECT f.*, o.name as opponent_name, o.level as opponent_level
            FROM fights f
            JOIN opponents o ON f.opponent_id = o.id
            WHERE f.leek_id = ?
            ORDER BY f.timestamp DESC
            LIMIT ?
        ''', (self.leek_id, limit))

        return [dict(row) for row in self.cursor.fetchall()]

    def export_to_csv(self, output_file: str = None) -> str:
        """
        Export fight history to CSV

        Args:
            output_file: Output filename (default: fight_history_{leek_id}.csv)

        Returns:
            Path to exported file
        """
        import csv

        if not output_file:
            output_file = f"fight_history_{self.leek_id}.csv"

        self.cursor.execute('''
            SELECT f.fight_id, f.timestamp, f.result, f.duration, f.actions_count, f.fight_url,
                   o.name as opponent_name, o.level as opponent_level
            FROM fights f
            JOIN opponents o ON f.opponent_id = o.id
            WHERE f.leek_id = ?
            ORDER BY f.timestamp DESC
        ''', (self.leek_id,))

        rows = self.cursor.fetchall()

        with open(output_file, 'w', newline='') as f:
            if rows:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                for row in rows:
                    writer.writerow(dict(row))

        return output_file

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


if __name__ == "__main__":
    # Example usage
    print("Fight Database Manager")
    print("=" * 60)
    print("This module provides database management for fight tracking.")
    print("Use it in your fight scripts or run the viewer tool.")
