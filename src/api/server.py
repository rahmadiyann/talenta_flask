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
