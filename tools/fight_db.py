#!/usr/bin/env python3
"""
FightDatabase - SQLite-based fight tracking system for LeekWars
Tracks opponent statistics, win rates, and provides smart opponent selection
"""

import sqlite3
import os
from datetime import datetime

class FightDatabase:
    def __init__(self, leek_id):
        """Initialize database for a specific leek"""
        self.leek_id = leek_id
        self.db_path = f"fight_history_{leek_id}.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        # Leek info table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS leek_info (
                leek_id INTEGER PRIMARY KEY,
                leek_name TEXT,
                leek_level INTEGER,
                last_updated TIMESTAMP
            )
        ''')

        # Fight history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS fight_history (
                fight_id INTEGER PRIMARY KEY,
                opponent_id INTEGER,
                opponent_name TEXT,
                opponent_level INTEGER,
                result TEXT,
                duration INTEGER,
                actions_count INTEGER,
                fight_url TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Opponent stats table (cached)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS opponent_stats (
                opponent_id INTEGER PRIMARY KEY,
                opponent_name TEXT,
                opponent_level INTEGER,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                draws INTEGER DEFAULT 0,
                total_fights INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                last_fought TIMESTAMP,
                last_updated TIMESTAMP
            )
        ''')

        # Create indexes for faster queries
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_opponent_id
            ON fight_history(opponent_id)
        ''')

        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_result
            ON fight_history(result)
        ''')

        self.conn.commit()

    def update_leek_info(self, leek_name, leek_level):
        """Update leek information"""
        self.cursor.execute('''
            INSERT OR REPLACE INTO leek_info
            (leek_id, leek_name, leek_level, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (self.leek_id, leek_name, leek_level, datetime.now()))
        self.conn.commit()

    def record_fight(self, fight_data):
        """Record a fight result and update opponent stats"""
        # Insert fight record
        self.cursor.execute('''
            INSERT OR REPLACE INTO fight_history
            (fight_id, opponent_id, opponent_name, opponent_level,
             result, duration, actions_count, fight_url, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            fight_data['fight_id'],
            fight_data['opponent_id'],
            fight_data['opponent_name'],
            fight_data['opponent_level'],
            fight_data['result'],
            fight_data.get('duration'),
            fight_data.get('actions_count', 0),
            fight_data['fight_url'],
            datetime.now()
        ))

        # Update opponent stats
        self._update_opponent_stats(fight_data['opponent_id'])

        self.conn.commit()

    def _update_opponent_stats(self, opponent_id):
        """Recalculate opponent statistics from fight history"""
        # Get all fights against this opponent
        self.cursor.execute('''
            SELECT result, opponent_name, opponent_level, MAX(timestamp) as last_fought
            FROM fight_history
            WHERE opponent_id = ?
            GROUP BY opponent_id
        ''', (opponent_id,))

        row = self.cursor.fetchone()
        if not row:
            return

        # Count wins/losses/draws
        self.cursor.execute('''
            SELECT
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN result = 'DRAW' THEN 1 ELSE 0 END) as draws,
                COUNT(*) as total_fights
            FROM fight_history
            WHERE opponent_id = ?
        ''', (opponent_id,))

        stats = self.cursor.fetchone()
        wins = stats['wins'] or 0
        losses = stats['losses'] or 0
        draws = stats['draws'] or 0
        total = stats['total_fights'] or 0

        # Calculate win rate
        win_rate = wins / total if total > 0 else 0.0

        # Update opponent stats table
        self.cursor.execute('''
            INSERT OR REPLACE INTO opponent_stats
            (opponent_id, opponent_name, opponent_level, wins, losses, draws,
             total_fights, win_rate, last_fought, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            opponent_id,
            row['opponent_name'],
            row['opponent_level'],
            wins,
            losses,
            draws,
            total,
            win_rate,
            row['last_fought'],
            datetime.now()
        ))

    def get_opponent_stats(self, opponent_id):
        """Get statistics for a specific opponent"""
        self.cursor.execute('''
            SELECT * FROM opponent_stats WHERE opponent_id = ?
        ''', (opponent_id,))

        row = self.cursor.fetchone()
        if not row:
            return None

        wins = row['wins']
        losses = row['losses']
        draws = row['draws']
        total = row['total_fights']
        win_rate = row['win_rate']

        # Determine status
        if total < 2:
            status = 'unknown'
        elif win_rate >= 0.7:
            status = 'beatable'
        elif win_rate <= 0.3:
            status = 'dangerous'
        else:
            status = 'even'

        return {
            'opponent_id': opponent_id,
            'opponent_name': row['opponent_name'],
            'opponent_level': row['opponent_level'],
            'wins': wins,
            'losses': losses,
            'draws': draws,
            'total_fights': total,
            'win_rate': win_rate,
            'status': status,
            'last_fought': row['last_fought']
        }

    def calculate_opponent_difficulty(self, opponent_id):
        """Calculate difficulty score for opponent (lower is easier)"""
        stats = self.get_opponent_stats(opponent_id)
        if not stats:
            return 50  # Unknown difficulty

        # Difficulty = 100 - (win_rate * 100)
        # 0 = always win, 100 = always lose
        win_rate = stats['win_rate']
        total_fights = stats['total_fights']

        # Adjust confidence based on number of fights
        if total_fights < 2:
            return 50  # Unknown
        elif total_fights < 5:
            # Less confident, pull toward 50
            confidence = total_fights / 5
            difficulty = (1 - win_rate) * 100
            return int(difficulty * confidence + 50 * (1 - confidence))
        else:
            # High confidence
            return int((1 - win_rate) * 100)

    def get_global_stats(self):
        """Get overall statistics across all fights"""
        # Total fights
        self.cursor.execute('SELECT COUNT(*) as total FROM fight_history')
        total_fights = self.cursor.fetchone()['total']

        if total_fights == 0:
            return {
                'total_fights': 0,
                'win_rate': 0.0,
                'opponents_tracked': 0,
                'beatable_opponents': 0,
                'dangerous_opponents': 0
            }

        # Win rate
        self.cursor.execute('''
            SELECT
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                COUNT(*) as total
            FROM fight_history
        ''')
        row = self.cursor.fetchone()
        win_rate = row['wins'] / row['total'] if row['total'] > 0 else 0.0

        # Opponent counts
        self.cursor.execute('SELECT COUNT(*) as total FROM opponent_stats')
        opponents_tracked = self.cursor.fetchone()['total']

        self.cursor.execute('''
            SELECT COUNT(*) as total FROM opponent_stats
            WHERE win_rate >= 0.7 AND total_fights >= 2
        ''')
        beatable_opponents = self.cursor.fetchone()['total']

        self.cursor.execute('''
            SELECT COUNT(*) as total FROM opponent_stats
            WHERE win_rate <= 0.3 AND total_fights >= 2
        ''')
        dangerous_opponents = self.cursor.fetchone()['total']

        return {
            'total_fights': total_fights,
            'win_rate': win_rate,
            'opponents_tracked': opponents_tracked,
            'beatable_opponents': beatable_opponents,
            'dangerous_opponents': dangerous_opponents
        }

    def get_preferred_opponents(self, all_opponents, strategy='smart'):
        """Filter opponents based on strategy"""
        if strategy == 'random':
            return all_opponents

        # Categorize opponents
        beatable = []
        unknown = []
        even = []
        dangerous = []

        for opp in all_opponents:
            opp_id = opp['id']
            stats = self.get_opponent_stats(opp_id)

            if not stats or stats['total_fights'] < 2:
                unknown.append(opp)
            elif stats['status'] == 'beatable':
                beatable.append(opp)
            elif stats['status'] == 'dangerous':
                dangerous.append(opp)
            else:
                even.append(opp)

        # Apply strategy
        if strategy == 'safe':
            # Only beatable and unknown
            return beatable + unknown

        elif strategy == 'smart':
            # Prefer beatable > unknown > some even, avoid dangerous
            return beatable + unknown + even[:len(even)//2]

        elif strategy == 'aggressive':
            # Fight all, but prefer beatable first
            return beatable + unknown + even + dangerous

        elif strategy == 'adaptive':
            # Check recent performance (last 10 fights)
            self.cursor.execute('''
                SELECT result FROM fight_history
                ORDER BY timestamp DESC LIMIT 10
            ''')
            recent = [row['result'] for row in self.cursor.fetchall()]

            if len(recent) >= 5:
                recent_win_rate = recent.count('WIN') / len(recent)

                if recent_win_rate >= 0.7:
                    # Doing well, be more aggressive
                    return beatable + unknown + even + dangerous[:len(dangerous)//2]
                elif recent_win_rate <= 0.3:
                    # Struggling, be more conservative
                    return beatable + unknown[:len(unknown)//2]
                else:
                    # Average, use smart strategy
                    return beatable + unknown + even[:len(even)//2]
            else:
                # Not enough data, use smart strategy
                return beatable + unknown + even[:len(even)//2]

        elif strategy == 'confident':
            # Only fight opponents with high confidence (5+ fights)
            confident = []
            for opp in all_opponents:
                stats = self.get_opponent_stats(opp['id'])
                if stats and stats['total_fights'] >= 5 and stats['status'] == 'beatable':
                    confident.append(opp)
            return confident if confident else beatable + unknown

        else:
            # Default to smart
            return beatable + unknown + even[:len(even)//2]

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.commit()
            self.conn.close()
