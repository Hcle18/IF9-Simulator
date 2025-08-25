# Global libraries
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union, Type, Tuple
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import zipfile
import fnmatch
import os
import re
import math