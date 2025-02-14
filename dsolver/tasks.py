from typing import Dict, Any
import subprocess
import signal
import os
import tempfile
import traceback
from browser import create_browser_tab
from config import CHROME_PATH, previous_dir, ALLOWED_HOSTS
from logger import get_task_logger
from port_lock import acquire_port, release_port

tasks: Dict[str, Dict[str, Any]] = {}

def handle_captcha(url: str, cid: str, port: int, task: Dict):
    task_id = task['task_id']
    logger = get_task_logger(task_id)
    logger.info(f"Starting captcha handling for URL: {url}")
    
    try:
        logger.info("Creating browser tab")
        tab, browser = create_browser_tab(url, cid, port)
        
        for attempt in range(30):
            if task['status'] == 'ready':
                logger.info("Task completed successfully")
                break
            tab.wait(1)
            if (attempt + 1) % 5 == 0:  # Log every 5 attempts
                logger.info(f"Waiting for task completion... Attempt {attempt + 1}/30")
                
        if task['status'] != 'ready':
            logger.error("Task timed out")
            task['status'] = 'error'
            task['value'] = 'timeout'
    except Exception as e:
        logger.error(f"Error handling captcha: {str(e)}")
        logger.error(traceback.format_exc())
        task['status'] = 'error'
        task['value'] = str(e)
        raise e
    finally:
        logger.info("Cleaning up browser tab")
        tab.stop()
        browser.close_tab(tab)

def process_url(proxy: str, task: Dict):
    cid = task['cid']
    task_id = task['task_id']
    logger = get_task_logger(task_id)
    logger.info(f"Starting URL processing for task {task_id}")
    logger.info(f"Using proxy: {proxy}")
    
    tmpdirname = tempfile.mkdtemp()
    logger.info(f"Created temporary directory: {tmpdirname}")
    
    port, proxy_port = None, None
    proxy_proc = None
    chrome_proc = None
    
    try:
        port, proxy_port = acquire_port()
        logger.info(f"Allocated debugging port: {port} and proxy port: {proxy_port}")
        
        proxy_command = [
            'proxy',
            '--proxy-pool', proxy,
            '--port', str(proxy_port),
            '--plugins', 'restrict_by_host_upstream.RestrictHostUpstream,proxy.plugin.ProxyPoolPlugin',
            '--restrict-by-host-upstream', '.*(' + "|".join(ALLOWED_HOSTS) + ').*',
        ]
        
        logger.info("Starting proxy process")
        proxy_proc = subprocess.Popen(proxy_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        commands = [
            CHROME_PATH,
            f'--remote-debugging-port={port}',
            f'--load-extension={previous_dir}/extensionv2',
            f'--user-data-dir={tmpdirname}',
            f'--proxy-server=http://127.0.0.1:{proxy_port}',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-default-apps',
        ]
        logger.info("Starting Chrome process")
        chrome_proc = subprocess.Popen(commands, start_new_session=True)
        
        try:
            handle_captcha(task['url'], cid, port, task)
        except Exception as e:
            logger.error(f"Error during captcha handling: {str(e)}")
            task['status'] = 'error'
        finally:
            logger.info("Terminating Chrome process")
            chrome_proc.kill()
            
        if proxy_proc and proxy_proc.poll() is None:
            logger.info("Terminating proxy process")
            os.kill(proxy_proc.pid, signal.SIGINT)
            proxy_proc.communicate()
    finally:
        logger.info("Cleaning up processes")
        if proxy_proc:
            try:
                proxy_proc.terminate()
            except Exception:
                pass
            try:
                proxy_proc.wait()
            except Exception:
                pass
        if port is not None and proxy_port is not None:
            release_port(port, proxy_port)
        logger.info(f"Removing temporary directory: {tmpdirname}")
        os.system(f'rm -rf {tmpdirname}') 