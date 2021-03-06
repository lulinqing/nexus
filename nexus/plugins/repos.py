#!/usr/bin/python
# Copyright (c) 2015 Red Hat, Inc. All rights reserved.
#
# This copyrighted material is made available to anyone wishing
# to use, modify, copy, or redistribute it subject to the terms
# and conditions of the GNU General Public License version 2.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the Free
# Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
# Boston, MA 02110-1301, USA.

import os
import sys
import platform
from nexus.lib.factory import SSHClient
from nexus.lib.factory import Threader
from nexus.lib import logger

class Repos():

    def __init__(self, options, conf_dict):

        self.username = conf_dict['beaker']['username']
        self.password = conf_dict['beaker']['password']
        nodes = conf_dict['jenkins']['existing_nodes']
        self.existing_nodes = [item.strip() for item in nodes.split(',')]

        self.jenkins_job_name = conf_dict['jenkins']['job_name']
        self.brew_tag = conf_dict['brew']['brew_tag']
        self.build_repo_tag = os.environ.get("BUILD_REPO_TAG")

    def my_build_repo(self, host, conf_dict):

        source = self.build_repo
        destination = "/etc/yum.repos.d/my_build.repo"

        logger.log.info("Copying %s to %s on %s" % (source, destination, host))
        ssh_c = SSHClient(hostname = host, username = \
                self.username, password = self.password)
        ssh_c.CopyFiles(source, destination)

    def copy_build_repo(self, host, conf_dict):
        """copy the brew build repo to all the existing nodes"""

        self.build_repo_file = self.build_repo_tag + ".repo"
        self.build_repo_url = os.environ.get("BUILD_REPO_URL")

        logger.log.info("Copying %s to %s" % (self.build_repo_file, host))
        repo = open(self.build_repo_file, "w")
        repo.write( "[" + self.build_repo_tag + "]\n");
        repo.write( "name=" + self.build_repo_tag + "\n" );
        repo.write( "baseurl=" + self.build_repo_url + "\n" );
        repo.write( "enabled=1\n") ;
        repo.write( "gpgcheck=0\n" );
        repo.write( "skip_if_unavailable=1\n" );
        repo.close()

        source = self.build_repo_file
        destination = "/etc/yum.repos.d/" + source

        logger.log.info("source file is %s" % source)
        logger.log.info("destination file is %s" % destination)

        ssh_c = SSHClient(hostname = host, username = \
                                  self.username, password = self.password)
        ssh_c.CopyFiles(source, destination)


    def copy_async_updates_repo(self, host, conf_dict):
        """copy the async updates repo to all the existing nodes"""

        try:
            logger.log.info("Checking platform.dist of %s to get the right batched repo" % host)
            ssh_c = SSHClient(hostname = host, username = \
                                      self.username, password = self.password)
            stdin, stdout, stderr = ssh_c.ExecuteCmd('python -c "import platform; \
                                                     print platform.dist()"')
            dist = stdout.read()
            dist = str(dist).replace('(','').replace(')','').replace("'", "").\
                   replace(',','')
            dist = dist.split()

            logger.log.info("Platform distribution for host %s is %s" % (host, dist))
            self.async_updates_url = conf_dict['async_repos'][dist[1]]

            self.build_repo_file = "async_updates_" + host + ".repo"

            logger.log.info("Creating async updates build repo file %s" % self.build_repo_file)
            repo = open(self.build_repo_file, "w")
            repo.write( "[" + "async_updates" + "]\n");
            repo.write( "name=" + "async_updates" + "\n" );
            repo.write( "baseurl=" + self.async_updates_url + "\n" );
            repo.write( "enabled=1\n") ;
            repo.write( "gpgcheck=0\n" );
            repo.write( "skip_if_unavailable=1\n" );
            repo.close()

            source = self.build_repo_file
            destination = "/etc/yum.repos.d/" + source

            logger.log.info("source file is %s" % source)
            logger.log.info("destination file is %s" % destination)

            ssh_c = SSHClient(hostname = host, username = \
                                      self.username, password = self.password)
            ssh_c.CopyFiles(source, destination)
        except KeyError, e:
            logger.log.error("%s key for async_updates_url does not exists in conf." % e)


    def run_repo_setup(self, options, conf_dict):
        """
        run async_updates repo function using threads per host.
        """

        threads = Threader()

        if self.build_repo_tag:
            logger.log.info("BUILD_REPO_TAG found in env")
            threads.gather_results([threads.get_item(self.copy_build_repo, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("BUILD_REPO_TAG not found in env")


        if options.build_repo:
            logger.log.info("Manual repo to be copied to resources.")
            self.build_repo = options.build_repo
            threads.gather_results([threads.get_item(self.my_build_repo, \
                                   host, conf_dict) for host in \
                                   self.existing_nodes])

        if "z-candidate" in self.brew_tag:
            logger.log.info("brew tag is for z-candidate, hence picking batched repo from conf.")
            threads.gather_results([threads.get_item(self.copy_async_updates_repo, \
                                    host, conf_dict) for host in \
                                    self.existing_nodes])
        else:
            logger.log.info("brew tag is not for z-candidate, hence not picking any batched repo from conf.")
