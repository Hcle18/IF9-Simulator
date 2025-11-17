# Global libraries
from dataclasses import dataclass, field
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
import json
import gc
import duckdb
import tempfile
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
import streamlit as st
