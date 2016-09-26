import './main.scss';
import template from './main.tpl.html';
import pack from '../../../package.json';

const MainComponent = {
  bindings: {
    user: '='
  },
  controller: function ($state, $window, userService) {
    let vm = this;
    vm.config = {
      env: $window.__env,
      package: pack
    };
    vm.goToDashboard = goToDashboard;
    vm.logout = logout;
    vm.showUserMenu = ($mdOpenMenu, ev) => { $mdOpenMenu(ev); };

    // functions 

    function goToDashboard() {
      $state.go('main.juror.dashboard', {}, {reload: true});
    }

    function logout() {
      userService.logout().then(() => {
        vm.user = {};
        $state.go('main.login');
      });
    }
  },
  template: template
};

export default () => {
  angular
    .module('montage')
    .component('montMain', MainComponent);
};
