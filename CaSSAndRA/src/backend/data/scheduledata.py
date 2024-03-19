import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass, field
from datetime import datetime

from .. comm import cmdlist
from . roverdata import robot
from . mapdata import Task, current_map
from . cfgdata import ScheduleCfg, schedulecfg
from .. map import path

@dataclass
class ScheduleTasks:
    active: bool = False
    dayweek: int = datetime.now().weekday()
    midnight: datetime = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    job_started: bool = False
    job_finished: bool = False
    start_failed_cnt: int = 0
    monday_task: Task = field(default_factory=lambda: Task())
    monday_time: list = field(default_factory=lambda: [12, 12])
    tuesday_task: Task = field(default_factory=lambda: Task())
    tuesday_time: list = field(default_factory=lambda: [12, 12])
    wednesday_task: Task = field(default_factory=lambda: Task())
    wednesday_time: list = field(default_factory=lambda: [12, 12])
    thursday_task: Task = field(default_factory=lambda: Task())
    thursday_time: list = field(default_factory=lambda: [12, 12])
    friday_task: Task = field(default_factory=lambda: Task())
    friday_time: list = field(default_factory=lambda: [12, 12])
    saturday_task: Task = field(default_factory=lambda: Task())
    saturday_time: list = field(default_factory=lambda: [12, 12])
    sunday_task: Task = field(default_factory=lambda: Task())
    sunday_time: list = field(default_factory=lambda: [12, 12])

    def create(self) -> None:
        self.monday_task.create()
        self.tuesday_task.create()
        self.wednesday_task.create()
        self.thursday_task.create()
        self.friday_task.create()
        self.saturday_task.create()
        self.sunday_task.create()
    
    def load_task_order(self, cfg: ScheduleCfg) -> None:
        self.monday_task.load_task_order(cfg.monday_tasks)
        self.tuesday_task.load_task_order(cfg.tuesday_tasks)
        self.wednesday_task.load_task_order(cfg.wednesday_tasks)
        self.thursday_task.load_task_order(cfg.thursday_tasks)
        self.friday_task.load_task_order(cfg.friday_tasks)
        self.saturday_task.load_task_order(cfg.saturday_tasks)
        self.sunday_task.load_task_order(cfg.sunday_tasks)
    
    def update_values_from_config(self) -> None:
        self.active = schedulecfg.active
        self.monday_time = schedulecfg.monday_time
        self.tuesday_time = schedulecfg.tuesday_time
        self.wednesday_time = schedulecfg.wednesday_time
        self.thursday_time= schedulecfg.thursday_time
        self.friday_time= schedulecfg.friday_time
        self.saturday_time= schedulecfg.saturday_time
        self.sunday_time= schedulecfg.sunday_time
    
    def check_new_day(self) -> None:
        if datetime.now().weekday() != self.dayweek:
            self.dayweek = datetime.now().weekday()
            self.midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            self.job_started = False
            self.job_finished = False
            self.start_failed_cnt = 0
            logger.info(f'New day, set weekday to: {self.dayweek}')
    
    def check_start_time(self) -> None:
        self.update_values_from_config()
        time_table = [self.monday_time,
                      self.tuesday_time,
                      self.wednesday_time,
                      self.thursday_time,
                      self.friday_time, 
                      self.saturday_time,
                      self.sunday_time]
        start_time_seconds = (datetime.now().replace(hour=int(time_table[self.dayweek][0]), minute=int(time_table[self.dayweek][0]%1*60), second=0, microsecond=0)
                              - self.midnight).seconds
        stop_time_seconds = (datetime.now().replace(hour=int(time_table[self.dayweek][1]), minute=int(time_table[self.dayweek][1]%1*60), second=0, microsecond=0)
                            - self.midnight).seconds
        now_seconds = (datetime.now() - self.midnight).seconds  
        if self.active and not self.job_started and not self.job_finished and (time_table[self.dayweek][1] - time_table[self.dayweek][0] != 0):
            if now_seconds >= start_time_seconds and now_seconds < stop_time_seconds:
                logger.info('Schedule command mow')
                self.create_start_cmd()
    
    def check_dock_time(self) -> None:
        self.update_values_from_config()
        time_table = [self.monday_time,
                      self.tuesday_time,
                      self.wednesday_time,
                      self.thursday_time,
                      self.friday_time, 
                      self.saturday_time,
                      self.sunday_time]
        stop_time_seconds = (datetime.now().replace(hour=int(time_table[self.dayweek][1]), minute=int(time_table[self.dayweek][1]%1*60), second=0, microsecond=0)
                     - self.midnight).seconds
        now_seconds = (datetime.now() - self.midnight).seconds
        if self.active and self.job_started and not self.job_finished and (time_table[self.dayweek][1] - time_table[self.dayweek][0] != 0):
            if now_seconds >= stop_time_seconds:
                self.create_dock_cmd()
    
    def create_start_cmd(self) -> None:
        if robot.job == 0 or robot.job == 2:
            tasks_order_table = [self.monday_task, self.tuesday_task, self.wednesday_task, self.thursday_task, self.friday_task, self.saturday_task, self.sunday_task]
            if tasks_order_table[self.dayweek].subtasks.empty and robot.last_task_name == 'mow':
                logger.info('Resume job')
                cmdlist.cmd_mow = True
                self.job_started = True
            elif not tasks_order_table[self.dayweek].subtasks.empty:
                logger.info('Create job from selected tasks')
                current_map.task_progress = 0
                current_map.calculating = True
                path.calc_task(tasks_order_table[self.dayweek].subtasks, tasks_order_table[self.dayweek].subtasks_parameters)
                current_map.calculating = False
                current_map.mowpath = current_map.preview
                current_map.mowpath['type'] = 'way'
                cmdlist.cmd_mow = True
                self.job_started = True
            else:
                logger.info(f'Schedule start not possible. Last command: {robot.last_task_name}')
                self.job_started = True
                self.job_finished = True
        else:
            logger.info(f'Schedule start command failed. Mower is in wrong state: {robot.status}')
            self.start_failed_cnt += 1
            if self.start_failed_cnt >= 5:
                self.job_finished = True
    
    def create_dock_cmd(self) -> None:
        if robot.job == 1:
            cmdlist.cmd_dock_schedule = True
            logger.info(f'Schedule dock command is send to mower')
        else:
            self.job_finished = True
            logger.info(f'Schedule job finished')
    
    def check(self) -> None:
        logger.info(f"Schedule: active: {self.active}, job started: {self.job_started}, job finished: {self.job_finished}, start failed cnt: {self.start_failed_cnt}")
        self.check_new_day()
        self.check_start_time()
        self.check_dock_time()

schedule_tasks = ScheduleTasks()