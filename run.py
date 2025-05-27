import os
import sys
from app import create_app, db
from app.seed import seed_data
from app.models import User, Room
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app.enums import ReservationStatus, ReservationLocationStatus
from app.models import Reservation
from flask import jsonify

relative_path = 'custom_library'
package_path = os.path.join(os.getcwd(), relative_path)
sys.path.append(package_path)

app = create_app()

def initialize_db(app):
    with app.app_context():
        db.create_all() # Create tables for our models
        print("Database initialized!")

        # Seed initial data
        if not Room.query.first():
            seed_data()
            print("Initial data has been seeded.")

def update_reservation_state():
    with app.app_context():
        now = datetime.now()

        # 오늘 날짜에 완료된 예약 상태를 업데이트
        reservations_to_update = Reservation.query.filter(
            Reservation.status == ReservationStatus.RESERVED,
            Reservation.end_time <= now
        ).all()

        if not reservations_to_update:
            print(f"[{now}] 업데이트할 예약 없음")
            return
        
        for reservation in reservations_to_update:
            reservation.status = ReservationStatus.COMPLETED
            print(f"Reservation ID {reservation.id} 상태를 'completed'로 변경")

        # 변경 사항 커밋
        db.session.commit()
        print(f"[{now}] 완료된 예약 상태 업데이트 완료!")

def reset_today_reserved_time():
    with app.app_context():
        users = User.query.all()

        for user in users:
            user.today_reserved_time = '00:00:00'
        
        db.session.commit()
        print("유저 하루 예약 시간 초기화 완료")


def check_location_verification_timeout():
    with app.app_context():
        now = datetime.now()

        # 기준 시각: 15분 전
        cutoff = now - timedelta(minutes=15)

        # 조건에 맞는 예약 조회
        expired_reservations = Reservation.query.filter(
            Reservation.status == ReservationStatus.RESERVED,
            Reservation.location_status == ReservationLocationStatus.UNVERIFIED,
            Reservation.start_time <= cutoff
        ).all()

        if not expired_reservations:
            print(f"[{now}] 인증 시간 초과된 예약 없음")
            return

        for reservation in expired_reservations:
            reservation.status = ReservationStatus.CANCELLED
            reservation.location_status = ReservationLocationStatus.FAILED

            print(f"[{now}] 예약 ID {reservation.id} 자동 취소됨 - 위치 인증 실패")
            print(f"[브로드캐스트] Room {reservation.room_id} - {reservation.start_time} 빈자리 발생!")

            # TODO: 관리자 알림 저장 로직 추가(DB or 로그 기록)
            # 예: AdminAlert.create(...)

        db.session.commit()
        print(f"[{now}] 인증 실패 예약 상태 업데이트 완료!")



# @app.errorhandler(404)
# def not_found(error):
#     print(error)
#     return jsonify({"error": "API 경로가 존재하지 않습니다."}), 404

# @app.errorhandler(404)
# def interner_error(error):
#     print(error)
#     return jsonify({"error": "서버 내부에서 오류가 발생하였습니다."}), 500

if __name__ == "__main__":
    initialize_db(app)
    update_reservation_state()

    # 스케줄러 초기화
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_reservation_state, 'cron', minute='0, 15, 30, 45')  # 매 00, 15, 30, 45분에 실행
    scheduler.add_job(reset_today_reserved_time, 'cron', hour='22')
    scheduler.add_job(check_location_verification_timeout, 'cron', minute='15,45')  # 매 15, 45분마다 위치 인증 실패한 예약을 취소시킴

    scheduler.start()

    print("스케줄러 시작!")
    try:
        # Flask 앱 실행
        app.run(host='0.0.0.0', port=5000, debug=True)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()  # 스케줄러 종료
        print("스케줄러 종료!")