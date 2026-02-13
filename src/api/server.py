"""
REST API server for controlling Talenta automation

This module provides a Flask-based REST API server that allows remote control
of the Talenta automation system. The server manages the automation state
in-memory and provides endpoints to enable, disable, and check the status.

Available Endpoints:
    POST /enable   - Enable the automation (allow scheduled jobs to execute)
    POST /disable  - Disable the automation (prevent scheduled jobs from executing)
    GET  /status   - Check the current automation state
    GET  /health   - Health check endpoint for container monitoring
    POST /clockin  - Trigger manual clock in
    POST /clockout - Trigger manual clock out
    GET  /schedule - Get shift schedule for a date range

State Management:
    The automation state is stored in-memory using a global dictionary.
    State resets to 'enabled' when the server restarts.

Usage Example:
    # Start the server
    python -m src.api.server

    # Enable automation
    curl -X POST http://localhost:5000/enable

    # Disable automation
    curl -X POST http://localhost:5000/disable

    # Check status
    curl http://localhost:5000/status

    # Health check
    curl http://localhost:5000/health

    # Manual clock in
    curl -X POST http://localhost:5000/clockin

    # Manual clock out
    curl -X POST http://localhost:5000/clockout

Note:
    This module can be run independently for testing purposes without
    starting the scheduler.
"""

from flask import Flask, request, jsonify
from src.core.logger import get_logger
from src.core import auth, location
from src.config import config_local

# Initialize Flask app
app = Flask(__name__)

# Disable Flask's default logger to avoid conflicts with custom logger
app.logger.disabled = True

# Preserve JSON key order in responses
app.config['JSON_SORT_KEYS'] = False

# Initialize logger using existing logger system
logger = get_logger('talenta_scheduler')

# Global state: in-memory automation state
# Using a dictionary to allow easy extension with additional fields
automation_state = {
    'enabled': True
}


def get_automation_state() -> bool:
    """
    Get the current automation state.

    This function provides a clean interface for the scheduler to check
    if jobs should execute without directly accessing the global variable.

    Returns:
        bool: True if automation is enabled, False otherwise
    """
    return automation_state['enabled']


@app.route('/enable', methods=['POST'])
def enable_automation():
    """
    Enable the automation (allow scheduled jobs to execute).

    Returns:
        JSON response with success status, message, and current state
    """
    automation_state['enabled'] = True
    logger.info("✅ Automation enabled via API")

    return jsonify({
        'success': True,
        'message': 'Automation enabled successfully',
        'state': automation_state
    }), 200


@app.route('/disable', methods=['POST'])
def disable_automation():
    """
    Disable the automation (prevent scheduled jobs from executing).

    Returns:
        JSON response with success status, message, and current state
    """
    automation_state['enabled'] = False
    logger.warning("⏸️  Automation disabled via API")

    return jsonify({
        'success': True,
        'message': 'Automation disabled successfully',
        'state': automation_state
    }), 200


@app.route('/status', methods=['GET'])
def check_status():
    """
    Check the current automation state.

    Returns:
        JSON response with success status, current state, and status message
    """
    logger.debug("📊 Status check requested")

    status_message = (
        "Automation is currently enabled"
        if automation_state['enabled']
        else "Automation is currently disabled"
    )

    return jsonify({
        'success': True,
        'state': automation_state,
        'message': status_message
    }), 200


@app.route('/favicon.ico')
def favicon():
    """Return empty response for favicon requests (suppresses browser 404 errors)."""
    return '', 204


@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for container monitoring.

    Returns:
        JSON response with health status
    """
    return jsonify({
        'status': 'healthy'
    }), 200


@app.route('/clockin', methods=['POST'])
def manual_clockin():
    """
    Trigger manual clock in via API.

    Returns:
        JSON response with clock in result
    """
    try:
        from src.cli.scheduler import clock_in_job as clock_in

        logger.info("⏰ Manual clock in triggered via API")

        # Get authentication cookies using shared function
        cookies = auth.get_cookies()

        # Get location using shared function
        config_dict = {
            'latitude': config_local.LATITUDE,
            'longitude': config_local.LONGITUDE
        }
        loc = location.get_location(config_dict)

        # Perform clock in
        clock_in(
            loc=loc,
            cookies=cookies
        )

        logger.info("✅ Manual clock in successful")

        return jsonify({
            'success': True,
            'message': 'Clock in successful'
        }), 200

    except Exception as error:
        logger.error(f"❌ Manual clock in failed: {error}")
        return jsonify({
            'success': False,
            'error': str(error),
            'message': 'Clock in failed'
        }), 500


@app.route('/clockout', methods=['POST'])
def manual_clockout():
    """
    Trigger manual clock out via API.

    Returns:
        JSON response with clock out result
    """
    try:
        from src.cli.scheduler import clock_out_job as clock_out

        logger.info("⏰ Manual clock out triggered via API")

        # Get authentication cookies using shared function
        cookies = auth.get_cookies()

        # Get location using shared function
        config_dict = {
            'latitude': config_local.LATITUDE,
            'longitude': config_local.LONGITUDE
        }
        loc = location.get_location(config_dict)

        # Perform clock out
        clock_out(
            loc=loc,
            cookies=cookies,
        )

        logger.info("✅ Manual clock out successful")

        return jsonify({
            'success': True,
            'message': 'Clock out successful'
        }), 200

    except Exception as error:
        logger.error(f"❌ Manual clock out failed: {error}")
        return jsonify({
            'success': False,
            'error': str(error),
            'message': 'Clock out failed'
        }), 500


@app.route('/schedule/ui', methods=['GET'])
def schedule_ui():
    """
    Serve a premium calendar UI for the schedule endpoint.
    """
    html = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Talenta Schedule Calendar</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        :root {
            --bg-primary: #0a0e27;
            --bg-secondary: #151933;
            --bg-glass: rgba(21, 25, 51, 0.7);
            --text-primary: #ffffff;
            --text-secondary: #a0aec0;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-pink: #ec4899;
            --accent-orange: #f59e0b;
            --accent-green: #10b981;
            --accent-red: #ef4444;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1729 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 20px;
            overflow-x: hidden;
            position: relative;
        }

        /* Animated background particles */
        .particles {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: 0;
            pointer-events: none;
        }

        .particle {
            position: absolute;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%);
            animation: float linear infinite;
        }

        @keyframes float {
            0% {
                transform: translateY(100vh) scale(0);
                opacity: 0;
            }
            10% {
                opacity: 1;
            }
            90% {
                opacity: 1;
            }
            100% {
                transform: translateY(-100vh) scale(1);
                opacity: 0;
            }
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }

        .header {
            text-align: center;
            margin-bottom: 40px;
            animation: fadeInDown 0.8s ease-out;
        }

        h1 {
            font-size: 3.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            letter-spacing: -1px;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 400;
        }

        .calendar-controls {
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 24px;
            padding: 24px 32px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
            animation: fadeInUp 0.8s ease-out 0.2s both;
        }

        .month-display {
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #fff 0%, #a0aec0 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .nav-buttons {
            display: flex;
            gap: 12px;
        }

        .nav-btn {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
            padding: 12px 24px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(10px);
            position: relative;
            overflow: hidden;
        }

        .nav-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }

        .nav-btn:hover::before {
            left: 100%;
        }

        .nav-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(59, 130, 246, 0.3);
            border-color: rgba(59, 130, 246, 0.5);
        }

        .nav-btn:active {
            transform: translateY(0);
        }

        .calendar-wrapper {
            animation: fadeInUp 0.8s ease-out 0.4s both;
        }

        .calendar {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 16px;
            margin-bottom: 32px;
        }

        .day-header {
            text-align: center;
            padding: 16px;
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
        }

        .day-cell {
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            min-height: 120px;
            padding: 16px;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            animation: scaleIn 0.5s cubic-bezier(0.4, 0, 0.2, 1) both;
        }

        .day-cell::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at center, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
            opacity: 0;
            transition: opacity 0.4s;
        }

        .day-cell:hover::before {
            opacity: 1;
        }

        .day-cell:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 20px 60px rgba(59, 130, 246, 0.3);
            border-color: rgba(59, 130, 246, 0.4);
        }

        .day-cell.other-month {
            opacity: 0.35;
            filter: grayscale(0.8) brightness(0.7);
            border: 1px solid rgba(255, 255, 255, 0.02);
        }

        .day-cell.other-month:hover {
            opacity: 0.5;
            filter: grayscale(0.6) brightness(0.8);
        }

        .day-cell.today {
            background: linear-gradient(135deg, rgba(59, 130, 246, 0.3) 0%, rgba(139, 92, 246, 0.3) 100%);
            border: 2px solid #3b82f6;
            box-shadow: 0 0 40px rgba(59, 130, 246, 0.4), inset 0 0 20px rgba(59, 130, 246, 0.2);
            animation: pulse 2s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% {
                box-shadow: 0 0 40px rgba(59, 130, 246, 0.4), inset 0 0 20px rgba(59, 130, 246, 0.2);
            }
            50% {
                box-shadow: 0 0 60px rgba(59, 130, 246, 0.6), inset 0 0 30px rgba(59, 130, 246, 0.3);
            }
        }

        .day-number {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text-primary);
        }

        .shift-badge {
            font-size: 0.75rem;
            padding: 6px 12px;
            border-radius: 8px;
            display: inline-block;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: relative;
            overflow: hidden;
            animation: slideIn 0.5s ease-out;
        }

        .shift-badge::after {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(45deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transform: rotate(45deg);
            animation: shine 3s infinite;
        }

        @keyframes shine {
            0% {
                left: -50%;
            }
            100% {
                left: 150%;
            }
        }

        .shift-wfa {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        }

        .shift-wfo {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
        }

        .shift-dayoff {
            background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%);
            box-shadow: 0 4px 15px rgba(107, 114, 128, 0.4);
        }

        .shift-holiday {
            background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
            box-shadow: 0 4px 15px rgba(236, 72, 153, 0.4);
        }

        .stats-panel {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
            animation: fadeInUp 0.8s ease-out 0.6s both;
        }

        .stat-card {
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 24px;
            text-align: center;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.05) 0%, transparent 70%);
            animation: rotate 10s linear infinite;
        }

        @keyframes rotate {
            0% {
                transform: rotate(0deg);
            }
            100% {
                transform: rotate(360deg);
            }
        }

        .stat-card:hover {
            transform: translateY(-5px);
            border-color: rgba(59, 130, 246, 0.3);
            box-shadow: 0 15px 40px rgba(59, 130, 246, 0.2);
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 800;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .stat-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 500;
        }

        .legend {
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 24px;
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 24px;
            animation: fadeInUp 0.8s ease-out 0.8s both;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            transition: transform 0.3s;
        }

        .legend-item:hover {
            transform: scale(1.05);
        }

        .legend-badge {
            width: 50px;
            height: 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .loading {
            text-align: center;
            padding: 80px 20px;
            color: var(--text-secondary);
            font-size: 1.2rem;
        }

        .loading::after {
            content: '...';
            animation: dots 1.5s steps(4, end) infinite;
        }

        @keyframes dots {
            0%, 20% {
                content: '.';
            }
            40% {
                content: '..';
            }
            60%, 100% {
                content: '...';
            }
        }

        .loading-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(10, 14, 39, 0.95);
            backdrop-filter: blur(10px);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 100;
            border-radius: 20px;
        }

        .spinner {
            width: 60px;
            height: 60px;
            border: 4px solid rgba(59, 130, 246, 0.1);
            border-top-color: #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-bottom: 20px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            color: var(--text-secondary);
            font-size: 1rem;
            font-weight: 500;
        }

        .progress-bar {
            width: 200px;
            height: 4px;
            background: rgba(59, 130, 246, 0.2);
            border-radius: 2px;
            overflow: hidden;
            margin-top: 12px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            border-radius: 2px;
            animation: progress 1.5s ease-in-out infinite;
        }

        @keyframes progress {
            0% {
                width: 0%;
                margin-left: 0%;
            }
            50% {
                width: 50%;
                margin-left: 25%;
            }
            100% {
                width: 0%;
                margin-left: 100%;
            }
        }

        .error {
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2) 0%, rgba(220, 38, 38, 0.2) 100%);
            border: 1px solid rgba(239, 68, 68, 0.5);
            color: #fca5a5;
            padding: 20px;
            border-radius: 16px;
            margin: 20px 0;
            text-align: center;
            backdrop-filter: blur(10px);
        }

        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes scaleIn {
            from {
                opacity: 0;
                transform: scale(0.8);
            }
            to {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-10px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }

        /* Skeleton loader */
        .skeleton {
            background: linear-gradient(90deg, #1a1f3a 25%, #2a2f4a 50%, #1a1f3a 75%);
            background-size: 200% 100%;
            animation: loading 1.5s ease-in-out infinite;
        }

        @keyframes loading {
            0% {
                background-position: 200% 0;
            }
            100% {
                background-position: -200% 0;
            }
        }

        /* Mobile and Tablet Responsive Design */
        @media (max-width: 1024px) {
            .container {
                max-width: 100%;
            }

            .stats-panel {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            body {
                padding: 12px;
            }

            h1 {
                font-size: 2rem;
                margin-bottom: 8px;
            }

            .subtitle {
                font-size: 0.9rem;
            }

            .header {
                margin-bottom: 24px;
            }

            .calendar-controls {
                flex-direction: column;
                gap: 16px;
                padding: 16px 20px;
            }

            .month-display {
                font-size: 1.5rem;
                text-align: center;
            }

            .nav-buttons {
                width: 100%;
                justify-content: space-between;
            }

            .nav-btn {
                flex: 1;
                padding: 10px 16px;
                font-size: 0.85rem;
            }

            .calendar {
                gap: 6px;
            }

            .day-header {
                padding: 8px;
                font-size: 0.7rem;
            }

            .day-cell {
                min-height: 70px;
                padding: 8px;
                border-radius: 12px;
            }

            .day-cell:hover {
                transform: translateY(-4px) scale(1.01);
            }

            .day-number {
                font-size: 1.1rem;
                margin-bottom: 4px;
            }

            .shift-badge {
                font-size: 0.6rem;
                padding: 4px 8px;
                border-radius: 6px;
            }

            .stats-panel {
                grid-template-columns: repeat(2, 1fr);
                gap: 12px;
                margin-bottom: 20px;
            }

            .stat-card {
                padding: 16px;
            }

            .stat-value {
                font-size: 1.8rem;
            }

            .stat-label {
                font-size: 0.75rem;
            }

            .legend {
                padding: 16px;
                gap: 12px;
                flex-direction: column;
                align-items: flex-start;
            }

            .legend-item {
                width: 100%;
                font-size: 0.85rem;
            }

            .legend-badge {
                width: 40px;
                height: 20px;
            }
        }

        @media (max-width: 480px) {
            body {
                padding: 8px;
            }

            h1 {
                font-size: 1.5rem;
            }

            .subtitle {
                font-size: 0.8rem;
            }

            .calendar {
                gap: 4px;
            }

            .day-header {
                padding: 6px 4px;
                font-size: 0.65rem;
            }

            .day-cell {
                min-height: 60px;
                padding: 6px;
                border-radius: 10px;
            }

            .day-number {
                font-size: 0.95rem;
            }

            .shift-badge {
                font-size: 0.55rem;
                padding: 3px 6px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                max-width: 100%;
            }

            .nav-btn {
                padding: 8px 12px;
                font-size: 0.8rem;
            }

            .month-display {
                font-size: 1.25rem;
            }

            .stats-panel {
                gap: 8px;
            }

            .stat-card {
                padding: 12px;
            }

            .stat-value {
                font-size: 1.5rem;
            }

            .stat-label {
                font-size: 0.7rem;
            }

            .legend {
                padding: 12px;
                gap: 10px;
            }

            .legend-item {
                font-size: 0.8rem;
            }

            .loading-overlay .spinner {
                width: 40px;
                height: 40px;
            }

            .loading-text {
                font-size: 0.9rem;
            }

            .progress-bar {
                width: 150px;
            }
        }

        /* Landscape mobile optimization */
        @media (max-width: 900px) and (orientation: landscape) {
            .day-cell {
                min-height: 60px;
            }

            .stats-panel {
                grid-template-columns: repeat(4, 1fr);
            }
        }

        /* Touch device optimizations */
        @media (hover: none) and (pointer: coarse) {
            .nav-btn {
                min-height: 44px;
                min-width: 44px;
            }

            .day-cell {
                min-height: 70px;
            }

            .day-cell:active {
                transform: scale(0.98);
                transition: transform 0.1s;
            }
        }

        /* High DPI displays */
        @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
            .shift-badge {
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
        }
    </style>
</head>
<body>
    <div class="particles" id="particles"></div>

    <div class="container">

        <div class="calendar-controls">
            <div class="month-display" id="current-month"></div>
            <div class="nav-buttons">
                <button class="nav-btn" onclick="previousMonth()">← Previous</button>
                <button class="nav-btn" onclick="today()">Today</button>
                <button class="nav-btn" onclick="nextMonth()">Next →</button>
            </div>
        </div>

        <div class="stats-panel" id="stats-panel"></div>

        <div class="calendar-wrapper" id="calendar-container">
            <div class="loading">Loading your schedule</div>
        </div>

        <div class="legend">
            <div class="legend-item">
                <div class="legend-badge shift-wfa"></div>
                <span>Work From Anywhere</span>
            </div>
            <div class="legend-item">
                <div class="legend-badge shift-wfo"></div>
                <span>Work From Office</span>
            </div>
            <div class="legend-item">
                <div class="legend-badge shift-dayoff"></div>
                <span>Day Off</span>
            </div>
            <div class="legend-item">
                <div class="legend-badge shift-holiday"></div>
                <span>Holiday</span>
            </div>
        </div>
    </div>

    <script>
        // Create floating particles
        function createParticles() {
            const particlesContainer = document.getElementById('particles');
            for (let i = 0; i < 30; i++) {
                const particle = document.createElement('div');
                particle.className = 'particle';
                particle.style.width = Math.random() * 100 + 50 + 'px';
                particle.style.height = particle.style.width;
                particle.style.left = Math.random() * 100 + '%';
                particle.style.animationDuration = Math.random() * 20 + 10 + 's';
                particle.style.animationDelay = Math.random() * 5 + 's';
                particlesContainer.appendChild(particle);
            }
        }
        createParticles();

        let currentDate = new Date();
        let isTransitioning = false;
        const weekDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const weekDaysShort = ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'];
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];

        // Schedule cache with 3-hour expiration
        const scheduleCache = {
            data: {},
            expirationTime: 3 * 60 * 60 * 1000, // 3 hours in milliseconds

            set: function(key, value) {
                this.data[key] = {
                    value: value,
                    timestamp: Date.now()
                };
                // Save to localStorage for persistence
                try {
                    localStorage.setItem('scheduleCache', JSON.stringify(this.data));
                } catch (e) {
                    console.warn('Failed to save cache to localStorage:', e);
                }
            },

            get: function(key) {
                // Load from localStorage on first access
                if (Object.keys(this.data).length === 0) {
                    try {
                        const stored = localStorage.getItem('scheduleCache');
                        if (stored) {
                            this.data = JSON.parse(stored);
                        }
                    } catch (e) {
                        console.warn('Failed to load cache from localStorage:', e);
                    }
                }

                const cached = this.data[key];
                if (!cached) return null;

                // Check if expired
                if (Date.now() - cached.timestamp > this.expirationTime) {
                    delete this.data[key];
                    return null;
                }

                return cached.value;
            },

            clear: function() {
                this.data = {};
                try {
                    localStorage.removeItem('scheduleCache');
                } catch (e) {
                    console.warn('Failed to clear cache from localStorage:', e);
                }
            }
        };

        function getShiftClass(shift) {
            if (!shift) return 'shift-dayoff';
            const s = shift.toLowerCase();
            if (s === 'wfa') return 'shift-wfa';
            if (s === 'wfo') return 'shift-wfo';
            if (s.includes('holiday')) return 'shift-holiday';
            return 'shift-dayoff';
        }

        function formatDate(date) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }

        function isToday(date) {
            const today = new Date();
            return date.getDate() === today.getDate() &&
                   date.getMonth() === today.getMonth() &&
                   date.getFullYear() === today.getFullYear();
        }

        async function renderCalendar() {
            if (isTransitioning) return;
            isTransitioning = true;

            const year = currentDate.getFullYear();
            const month = currentDate.getMonth();

            // Show loading overlay
            const container = document.getElementById('calendar-container');
            const loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'loading-overlay';
            loadingOverlay.innerHTML = `
                <div class="spinner"></div>
                <div class="loading-text">Loading schedule data</div>
                <div class="progress-bar">
                    <div class="progress-fill"></div>
                </div>
            `;
            container.style.position = 'relative';
            container.appendChild(loadingOverlay);

            // Update header with animation
            const monthDisplay = document.getElementById('current-month');
            monthDisplay.style.opacity = '0';
            setTimeout(() => {
                monthDisplay.textContent = `${monthNames[month]} ${year}`;
                monthDisplay.style.transition = 'opacity 0.5s';
                monthDisplay.style.opacity = '1';
            }, 200);

            // Get first and last day of month
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);

            // Get first Monday before or on first day of month
            const startDate = new Date(firstDay);
            const dayOfWeek = startDate.getDay();
            const diff = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
            startDate.setDate(startDate.getDate() - diff);

            // Get last Sunday after or on last day of month
            const endDate = new Date(lastDay);
            const endDayOfWeek = endDate.getDay();
            const endDiff = endDayOfWeek === 0 ? 0 : 7 - endDayOfWeek;
            endDate.setDate(endDate.getDate() + endDiff);

            // Fetch schedule data
            const scheduleData = await fetchScheduleData(formatDate(startDate), formatDate(endDate));

            // Calculate statistics - only for current month dates
            let wfaCount = 0, wfoCount = 0, offCount = 0, holidayCount = 0;
            Object.entries(scheduleData).forEach(([dateStr, day]) => {
                // Parse the date and check if it belongs to current month
                const [y, m, d] = dateStr.split('-').map(Number);
                if (y === year && m === (month + 1)) {
                    if (day.shift) {
                        const shift = day.shift.toLowerCase();
                        if (shift === 'wfa') wfaCount++;
                        else if (shift === 'wfo') wfoCount++;
                        else if (shift.includes('holiday')) holidayCount++;
                        else offCount++;
                    }
                }
            });

            // Render stats
            const statsPanel = document.getElementById('stats-panel');
            statsPanel.innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${wfaCount}</div>
                    <div class="stat-label">WFA Days</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${wfoCount}</div>
                    <div class="stat-label">WFO Days</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${holidayCount}</div>
                    <div class="stat-label">Holidays</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${offCount}</div>
                    <div class="stat-label">Days Off</div>
                </div>
            `;

            // Build calendar HTML
            let html = '<div class="calendar">';

            // Day headers
            weekDaysShort.forEach(day => {
                html += `<div class="day-header">${day}</div>`;
            });

            // Day cells
            let currentDay = new Date(startDate);
            let cellIndex = 0;
            while (currentDay <= endDate) {
                const dateStr = formatDate(currentDay);
                const isCurrentMonth = currentDay.getMonth() === month;
                const isTodayDate = isToday(currentDay);

                const schedule = scheduleData[dateStr];
                const shift = schedule?.shift || null;
                const shiftClass = getShiftClass(shift);

                let cellClass = 'day-cell';
                if (!isCurrentMonth) cellClass += ' other-month';
                if (isTodayDate) cellClass += ' today';

                html += `
                    <div class="${cellClass}" style="animation-delay: ${cellIndex * 0.03}s">
                        <div class="day-number">${currentDay.getDate()}</div>
                        ${shift ? `<div class="shift-badge ${shiftClass}">${shift}</div>` : ''}
                    </div>
                `;

                currentDay.setDate(currentDay.getDate() + 1);
                cellIndex++;
            }

            html += '</div>';

            // Remove loading overlay and show calendar
            setTimeout(() => {
                container.innerHTML = html;
                container.style.position = 'relative';
                isTransitioning = false;
            }, 200);
        }

        async function fetchScheduleData(startDate, endDate) {
            // Create cache key from date range
            const cacheKey = `${startDate}_${endDate}`;

            // Check cache first
            const cached = scheduleCache.get(cacheKey);
            if (cached) {
                console.log('📦 Using cached schedule data for', startDate, 'to', endDate);
                return cached;
            }

            // Fetch from API if not cached
            try {
                console.log('🌐 Fetching schedule data from API for', startDate, 'to', endDate);
                const response = await fetch(`/schedule?start_date=${startDate}&end_date=${endDate}`);
                const data = await response.json();

                if (!data.success) {
                    console.error('Failed to fetch schedule:', data.message);
                    return {};
                }

                const scheduleMap = {};
                data.schedule.forEach(item => {
                    scheduleMap[item.date] = item;
                });

                // Store in cache
                scheduleCache.set(cacheKey, scheduleMap);

                return scheduleMap;
            } catch (err) {
                console.error('Error fetching schedule:', err);
                document.getElementById('calendar-container').innerHTML =
                    `<div class="error">⚠️ Error loading schedule: ${err.message}</div>`;
                return {};
            }
        }

        function previousMonth() {
            currentDate.setMonth(currentDate.getMonth() - 1);
            renderCalendar();
        }

        function nextMonth() {
            currentDate.setMonth(currentDate.getMonth() + 1);
            renderCalendar();
        }

        function today() {
            currentDate = new Date();
            renderCalendar();
        }

        // Initial render
        renderCalendar();
    </script>
</body>
</html>
    '''
    return html


@app.route('/schedule', methods=['GET'])
def get_schedule():
    """
    Get shift schedule for a single date or date range.

    Query parameters (one of the following):
        date: Single date in YYYY-MM-DD format
        OR
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        JSON response with shift info for single date or list of shifts for date range

    Examples:
        GET /schedule?date=2026-01-20
        GET /schedule?start_date=2026-01-20&end_date=2026-01-25
    """
    from src.api.talenta import get_shifts_for_date_range, get_shift_for_date

    single_date = request.args.get('date')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Handle single date request
    if single_date:
        try:
            logger.info(f"📅 Schedule request for single date: {single_date}")

            shift = get_shift_for_date(single_date)

            if not shift:
                return jsonify({
                    'success': False,
                    'message': f'No schedule data found for {single_date}'
                }), 404

            office_hour = shift.get('office_hour_name', '')
            is_holiday = shift.get('holiday', False)
            is_work = office_hour.lower() in ['wfa', 'wfo'] and not is_holiday

            return jsonify({
                'success': True,
                'date': single_date,
                'shift': office_hour,
                'is_work_day': is_work,
                'holiday': is_holiday
            }), 200

        except Exception as error:
            logger.error(f"❌ Schedule fetch failed: {error}")
            return jsonify({
                'success': False,
                'error': str(error),
                'message': 'Failed to fetch schedule'
            }), 500

    # Handle date range request
    if not start_date or not end_date:
        return jsonify({
            'success': False,
            'error': 'Missing required parameters',
            'message': 'Provide either "date" for single date, or both "start_date" and "end_date" for a range (YYYY-MM-DD format)'
        }), 400

    try:
        logger.info(f"📅 Schedule request: {start_date} to {end_date}")

        shifts = get_shifts_for_date_range(start_date, end_date)

        if not shifts:
            return jsonify({
                'success': False,
                'message': 'No schedule data found for the specified date range'
            }), 404

        # Count work days and off days
        work_days = sum(1 for s in shifts if s.get('is_work_day') is True)
        off_days = sum(1 for s in shifts if s.get('is_work_day') is False)

        return jsonify({
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': len(shifts),
            'work_days': work_days,
            'off_days': off_days,
            'schedule': shifts
        }), 200

    except Exception as error:
        logger.error(f"❌ Schedule fetch failed: {error}")
        return jsonify({
            'success': False,
            'error': str(error),
            'message': 'Failed to fetch schedule'
        }), 500


@app.errorhandler(Exception)
def handle_error(error):
    """
    Global error handler for all unhandled exceptions.

    Args:
        error: The exception that was raised

    Returns:
        JSON response with error details
    """
    logger.error(f"Error processing request: {str(error)}", exc_info=True)

    return jsonify({
        'success': False,
        'error': str(error),
        'message': 'An error occurred while processing the request'
    }), 500


if __name__ == '__main__':
    """
    Main block for independent testing.
    Allows running the server without the scheduler.
    """
    logger.info("🚀 Starting Talenta automation control server...")
    logger.info("Available endpoints:")
    logger.info("  POST /enable   - Enable the automation")
    logger.info("  POST /disable  - Disable the automation")
    logger.info("  GET  /status   - Check automation status")
    logger.info("  GET  /health   - Health check")
    logger.info("  POST /clockin  - Trigger manual clock in")
    logger.info("  POST /clockout - Trigger manual clock out")
    logger.info("  GET  /schedule - Get shift schedule (params: start_date, end_date)")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
